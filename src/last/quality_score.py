"""Run an unchanged official VBench2 dimension, retaining applicability failures."""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
from .quality_paths import scorer_paths


def summarize(result, rows, dimension):
    expected = [r['video_list'][0] for r in rows] if dimension == 'Diversity' else [v for r in rows for v in r['video_list']]
    if len(set(expected)) != len(expected):
        raise ValueError('Duplicate scoring units')
    details = result[1]
    paths = [r['video_path'] for r in details]
    if len(paths) != len(set(paths)) or set(paths) != set(expected):
        raise ValueError('Official scorer omitted, duplicated or added scoring units')
    values = [float(r['video_results']) for r in details]
    valid = [v for v in values if math.isfinite(v) and 0 <= v <= 1]
    invalid = [v for v in values if not math.isfinite(v) or (v != -1 and not 0 <= v <= 1)]
    if invalid:
        raise ValueError('Unexpected official score range')
    return dict(expected_units=len(expected), valid_units=len(valid), not_applicable_units=values.count(-1),
                unit='prompt' if dimension == 'Diversity' else 'video',
                mean=sum(valid)/len(valid) if valid else None,
                all_applicable=len(valid) == len(expected))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('upstream', 'inputs', 'submodules', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dimension', required=True)
    p.add_argument('--device', default='cuda')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--llava-siglip',type=Path,help='Explicit local SigLIP directory for the bundled LLaVA loader')
    p.add_argument('--llava-attention',choices=['sdpa','flash_attention_2'],default='sdpa')
    p.add_argument('--llava-vision-batch',type=int,default=0,help='Explicit per-image SigLIP microbatch; 0 keeps original full batch')
    p.add_argument('--cotracker-checkpoint', type=Path,
                   help='Explicit local CoTracker2 loading adapter; bundled upstream code, window_len=8')
    p.add_argument('--allow-partial-diagnostic', action='store_true')
    a = p.parse_args()
    if a.llava_vision_batch<0 or (a.llava_vision_batch and not a.llava_siglip):p.error('Vision batching requires local SigLIP and a nonnegative size')
    upstream = a.upstream.resolve(); inputs = a.inputs.resolve()
    coverage = json.loads((inputs/'coverage.json').read_text())
    if not coverage['complete'] and not a.allow_partial_diagnostic:
        p.error('Incomplete input coverage; explicit diagnostic flag required')
    metadata = inputs/f'{a.dimension}.json'
    rows = json.loads(metadata.read_text())
    if not rows or any(not r['video_list'] for r in rows):
        p.error('Empty scoring input')
    if a.dimension == 'Diversity' and any(len(r['video_list']) != 20 for r in rows):
        p.error('Official paper Diversity requires 20 seeds per prompt')
    for row in rows:
        for video in row['video_list']:
            if not Path(video).is_file():
                p.error('Missing input video: '+video)
    submodules = json.loads(a.submodules.read_text())
    output = a.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    record = dict(status='running', dimension=a.dimension, device=a.device, seed=a.seed,
                  complete_input_coverage=coverage['complete'],
                  metadata_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest(),
                  submodules_sha256=hashlib.sha256(a.submodules.read_bytes()).hexdigest(),
                  scope='Official dimension function; not a complete V-score')
    start = time.monotonic()
    def save():
        record['seconds'] = time.monotonic()-start
        (output/'receipt.json').write_text(json.dumps(record, indent=2, allow_nan=False))
    save()
    try:
        import torch
        import numpy as np
        import random
        torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
        paths = list(map(str, scorer_paths(upstream)))
        sys.path[:0] = paths
        record['bundled_dependency_paths'] = paths
        if a.cotracker_checkpoint:
            if a.dimension not in ('Camera_Motion', 'Multi-View_Consistency'):
                raise ValueError('CoTracker adapter is only for tracker dimensions')
            checkpoint = a.cotracker_checkpoint.resolve()
            bundled = upstream/'vbench2/third_party'
            sys.path.insert(0, str(bundled))
            from cotracker.predictor import CoTrackerPredictor
            import cotracker.predictor as predictor
            if not Path(predictor.__file__).resolve().is_relative_to(bundled):
                raise RuntimeError('CoTracker imported from a different checkout')
            record['model_loading_adapter'] = dict(
                name='local CoTracker2; bundled upstream predictor; window_len=8',
                checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                source_sha256={str(f.relative_to(bundled)):hashlib.sha256(f.read_bytes()).hexdigest()
                               for f in sorted((bundled/'cotracker').rglob('*.py'))})
            def local_tracker(repo, model, *args, **kwargs):
                if repo != 'facebookresearch/co-tracker' or model != 'cotracker2' or args or kwargs:
                    raise ValueError('Unexpected torch.hub request; refusing implicit fallback')
                network = CoTrackerPredictor(checkpoint=None, window_len=8, v2=True)
                network.model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True), strict=True)
                return network
            torch.hub.load = local_tracker
        module_name = a.dimension.lower().replace('-', '_')
        module = importlib.import_module('vbench2.'+module_name)
        source = Path(module.__file__).resolve()
        if not source.is_relative_to(upstream):
            raise RuntimeError('Scorer imported from a different checkout')
        record['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        if a.llava_siglip:
            if not hasattr(module,'load_pretrained_model'):
                raise ValueError('Selected dimension does not use the LLaVA loader')
            from llava.model import llava_arch
            from llava.model.multimodal_encoder.siglip_encoder import SigLipVisionTower
            tower_path=a.llava_siglip.resolve()
            if not (tower_path/'config.json').is_file():raise ValueError('Missing local SigLIP config')
            bundled=upstream/'vbench2/third_party/LLaVA_NeXT'
            if not Path(llava_arch.__file__).resolve().is_relative_to(bundled):
                raise RuntimeError('LLaVA imported from a different checkout')
            original_tower=llava_arch.build_vision_tower
            def local_tower(config,**kwargs):
                if getattr(config,'mm_vision_tower',None)==str(tower_path):
                    tower=SigLipVisionTower(str(tower_path),vision_tower_cfg=config,**kwargs)
                    if a.llava_vision_batch:
                        from .vision_batch import forward_images
                        original_forward=tower.forward
                        tower.forward=lambda images:forward_images(original_forward,images,a.llava_vision_batch)
                    return tower
                return original_tower(config,**kwargs)
            llava_arch.build_vision_tower=local_tower
            original_loader=module.load_pretrained_model
            def local_loader(*args,**kwargs):
                kwargs.update(attn_implementation=a.llava_attention,overwrite_config={'mm_vision_tower':str(tower_path)})
                return original_loader(*args,**kwargs)
            module.load_pretrained_model=local_loader
            record['llava_loading_adapter']=dict(attention=a.llava_attention,
                vision_microbatch=a.llava_vision_batch,
                siglip_path=str(tower_path),
                siglip_files={str(f.relative_to(tower_path)):hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in sorted(tower_path.rglob('*')) if f.is_file() and '.cache' not in f.parts},
                bundled_source_sha256={str(f.relative_to(bundled)):hashlib.sha256(f.read_bytes()).hexdigest()
                                      for f in sorted((bundled/'llava').rglob('*.py'))},
                scope='Explicit weight location and attention backend; official questions, frames and scoring unchanged')
            save()
        previous = Path.cwd()
        try:
            os.chdir(upstream)
            result = getattr(module, 'compute_'+module_name)(str(metadata), torch.device(a.device), submodules)
        finally:
            os.chdir(previous)
        def plain(value):
            if isinstance(value, dict): return {k: plain(v) for k,v in value.items()}
            if isinstance(value, (list, tuple)): return [plain(v) for v in value]
            if hasattr(value, 'tolist'): return value.tolist()
            return value
        result = plain(result)
        (output/'official_result.json').write_text(json.dumps(result, indent=2))
        record.update(summarize(result, rows, a.dimension), status='completed')
        save()
    except BaseException:
        record.update(status='failed', error=traceback.format_exc()); save(); raise


if __name__ == '__main__':
    main()
