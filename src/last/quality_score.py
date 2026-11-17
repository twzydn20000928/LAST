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
    p.add_argument('--allow-partial-diagnostic', action='store_true')
    a = p.parse_args()
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
        sys.path.insert(0, str(upstream))
        module_name = a.dimension.lower().replace('-', '_')
        module = importlib.import_module('vbench2.'+module_name)
        source = Path(module.__file__).resolve()
        if not source.is_relative_to(upstream):
            raise RuntimeError('Scorer imported from a different checkout')
        record['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
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
