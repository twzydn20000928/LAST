"""Warm-model paired generation timing; requires an exclusive GPU."""
import argparse
import hashlib
import json
import os
import traceback
from pathlib import Path
from .paired_timing import measure_pairs
from .reader_timing import require_exclusive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family', choices=['hunyuan', 'wan22'], required=True)
    p.add_argument('--mode', choices=['i2v', 't2v'], required=True)
    p.add_argument('--method', choices=['last', 'lfg', 'sigmark', 'videoshield', 'videomark'], required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--key', type=Path)
    p.add_argument('--upstream', type=Path)
    p.add_argument('--manifest', type=Path, default=Path('configs/sigmark_source_manifest.json'))
    p.add_argument('--message', type=Path, required=True)
    p.add_argument('--order', choices=['AB', 'BA'], required=True)
    p.add_argument('--protocol', choices=['main', 'supplement'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    native = a.method in ('sigmark', 'videoshield', 'videomark')
    if native and (a.upstream is None or a.key is not None):
        p.error('Native timing requires --upstream and uses native key setup, not --key')
    if not native and a.key is None:
        p.error('LAST/LFG require --key')
    os.umask(0o077)
    a.output.mkdir(parents=True, exist_ok=False)
    record = dict(status='preparing', family=a.family, mode=a.mode,
                  method=a.method, protocol=a.protocol, order=a.order, pairs=[])
    def save():
        temp = a.output / 'receipt.tmp'
        temp.write_text(json.dumps(record, indent=2))
        temp.replace(a.output / 'receipt.json')
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    save()
    try:
        require_exclusive()
        import numpy as np
        import torch
        from PIL import Image
        from diffusers import (HunyuanVideoPipeline, HunyuanVideoImageToVideoPipeline,
            WanPipeline, WanImageToVideoPipeline, AutoencoderKLHunyuanVideo,
            AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, UniPCMultistepScheduler)
        from .carriers import codebook
        from .coding import BCH512
        from .baseline_generate import denormalize_endpoint
        from .elmc import embed
        from .lfg import watermark
        from .lfg_schedulers import LFGFlowEuler, LFGUniPC
        torch.set_num_threads(4)
        case = json.loads(a.case.read_text())
        key, message = a.key.read_bytes() if a.key else None, a.message.read_bytes()
        if (key is not None and len(key) != 32) or len(message) != 64:
            raise ValueError('Require a32byte key and64byte message')
        input_hashes = {str(path): sha(path) for path in (a.case, a.key, a.message) if path is not None}
        source = {path.name: sha(path) for path in Path(__file__).parent.glob('*.py')}
        signs = BCH512().encode(np.unpackbits(np.frombuffer(message, dtype=np.uint8))).astype(np.float32)*2-1
        codes = torch.from_numpy(codebook(key)) if a.method == 'last' else None
        spread = watermark(key, signs).cuda() if a.method == 'lfg' else None
        native_writer = None
        if native:
            from .baseline_probe import load_class
            manifest = json.loads(a.manifest.read_text())
            wm_cls = load_class(a.method, a.upstream, manifest)
            seed = int(case['seed'])
            torch.manual_seed(seed)
            np.random.seed(seed)
            native_writer = wm_cls(video_h=512, video_w=512, video_f=65, latent_c=16,
                vae_scale_factor_spatial=8, vae_scale_factor_temporal=4,
                ch_factor=2, hw_factor=8, fr_factor=16, batch_size=1,
                seed=seed, dtype=torch.float32, device='cpu')
            geometry = native_writer.get_watermark_message_shape()
            if int(np.prod(geometry)) != 512:
                raise ValueError('Unexpected native message geometry')
            native_message = np.unpackbits(np.frombuffer(message, dtype=np.uint8)).reshape(geometry)
            native_numpy_state, native_torch_state = np.random.get_state(), torch.get_rng_state()
            record.update(upstream_commit=manifest['commit'],
                native_setup='Constructor PRC key setup excluded; per-video encoding and VideoShield ephemeral key/nonce sampling included',
                native_scope='Pinned SIGMark baseline implementation; generation timing only, no registration-based extraction')
            input_hashes[str(a.manifest)] = sha(a.manifest)
        cls = ((HunyuanVideoImageToVideoPipeline if a.mode == 'i2v' else HunyuanVideoPipeline)
               if a.family == 'hunyuan' else (WanImageToVideoPipeline if a.mode == 'i2v' else WanPipeline))
        vae_cls = AutoencoderKLHunyuanVideo if a.family == 'hunyuan' else AutoencoderKLWan
        vae = vae_cls.from_pretrained(a.model_dir, subfolder='vae', torch_dtype=torch.float32, local_files_only=True)
        vae.enable_tiling()
        pipe = cls.from_pretrained(a.model_dir, vae=vae, torch_dtype=torch.bfloat16,
                                  local_files_only=True, low_cpu_mem_usage=True)
        scheduler_cls = FlowMatchEulerDiscreteScheduler if a.family == 'hunyuan' else UniPCMultistepScheduler
        settings = dict(shift=7) if a.family == 'hunyuan' else dict(flow_shift=5, use_flow_sigmas=True, prediction_type='flow_prediction')
        config = dict(scheduler_cls.from_config(pipe.scheduler.config, **settings).config)
        pipe.enable_sequential_cpu_offload(device='cuda:0')
        pipe.set_progress_bar_config(disable=True)
        image = None
        if a.mode == 'i2v':
            image_path = Path(case['image'])
            input_hashes[str(image_path)] = sha(image_path)
            image = Image.open(image_path).convert('RGB').resize((512,512))
        seed = int(case['seed'])
        shape_checks = []

        def operation(marked):
            # Fresh schedulers avoid UniPC history leaking between paired calls.
            guided_cls = LFGFlowEuler if a.family == 'hunyuan' else LFGUniPC
            pipe.scheduler = (guided_cls if marked and a.method == 'lfg' else scheduler_cls).from_config(config)
            if marked and a.method == 'lfg':
                pipe.scheduler.spread = spread
                pipe.scheduler.alpha, pipe.scheduler.late_steps = .15, 10
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            np.random.seed(seed)
            if marked and native_writer is not None:
                np.random.set_state(native_numpy_state)
                torch.set_rng_state(native_torch_state)
                if a.method == 'videoshield':
                    native_writer.maintained_info = []
                elif a.method == 'videomark':
                    native_writer.maintained_info['watermark_messages'] = []
                initial = native_writer.create_watermarked_latents(native_message).to('cuda', torch.bfloat16)
            else:
                initial = torch.randn(1,16,17,64,64, generator=torch.Generator().manual_seed(seed), dtype=torch.bfloat16).cuda()
            # Match the ordinary adapter's reset immediately before diffusion.
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            kwargs = dict(prompt=[case['prompt']], height=512, width=512, num_frames=65,
                          num_inference_steps=50, guidance_scale=6 if a.family == 'hunyuan' else 5,
                          latents=initial,
                          output_type='latent', return_dict=False)
            if image is not None:
                kwargs['image'] = image
            with torch.inference_mode():
                z = pipe(**kwargs)[0].float()
                if tuple(z.shape) != (1,16,17,64,64):
                    raise ValueError('Unexpected endpoint shape')
                if marked and a.method == 'last':
                    z = embed(z, codes, signs, mu=.5)
                z = denormalize_endpoint(z, vae.config, a.family)
                pixels = vae.decode(z.float(), return_dict=False)[0]
                if tuple(pixels.shape) != (1,3,65,512,512):
                    raise ValueError('Unexpected decoded shape')
                # Same final conversion as smoke, but no codec or file writes.
                frames = pipe.video_processor.postprocess_video(pixels, output_type='pil')[0]
                shape_checks.append(len(frames))
                del frames, pixels, z
        record.update(status='measuring', case_sha256=sha(a.case), seed=seed,
                      source_sha256=source, offload='sequential',
                      gpu=torch.cuda.get_device_name(0), model_directory=str(a.model_dir),
                      includes=['seed/noise preparation', 'scheduler reset', 'prompt encoding', '50-step sampling', 'watermark operation', 'VAE decode', 'PIL conversion'],
                      excludes=['model loading', 'one-time secret/carrier setup', 'input image file read', 'MP4 encoding and disk export'],
                      validation='Actual exclusive-GPU parity validation required; not a completed five-method table')
        save()
        def persist(row):
            record['pairs'].append(row)
            save()
        result = measure_pairs(lambda: operation(False), lambda: operation(True),
            torch.cuda.synchronize, require_exclusive, order=a.order, warmup_pairs=2,
            measured_pairs=2 if a.protocol == 'main' else 5, on_pair=persist)
        if any(sha(Path(path)) != digest for path, digest in input_hashes.items()):
            raise ValueError('Input changed during timing')
        if source != {path.name: sha(path) for path in Path(__file__).parent.glob('*.py')}:
            raise ValueError('Source changed during timing')
        if native:
            from .upstream import verify
            verify(a.upstream, manifest)
        record.update(status='completed', measurement=result, decoded_frame_counts=shape_checks)
        save()
    except BaseException:
        record.update(status='failed', error=traceback.format_exc())
        save()
        raise


if __name__ == '__main__':
    main()
