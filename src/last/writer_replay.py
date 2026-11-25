"""Replay a writer intervention on a verified, private real generation endpoint."""
import argparse
import hashlib
import json
import os
import shutil
import time
import traceback
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_source(run):
    r = json.loads((run / 'receipt.json').read_text())
    if r.get('status') != 'completed' or r.get('method') != 'last':
        raise ValueError('Require a completed LAST endpoint generation')
    for name, field in [('endpoint.pt', 'endpoint_sha256'), ('codes.pt', 'codebook_sha256'),
                        ('marked.mp4', 'marked_sha256')]:
        if not r.get(field) or digest(run / name) != r[field]:
            raise ValueError('Missing or mismatched source artifact: ' + name)
    if r['family'] not in ('hunyuan', 'wan22'):
        raise ValueError('Unsupported family')
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fixed-target', action='store_true')
    p.add_argument('--uniform-profile', action='store_true',
                   help='Use the same margin in all message groups (supplementary Table 16)')
    p.add_argument('--memory-gib', type=float, default=8)
    a = p.parse_args()
    source = validate_source(a.run)
    if a.model_dir.resolve() != Path(source['model_directory']).resolve():
        raise ValueError('Replay requires the same local model directory as source generation')
    # Snapshot every paired input, including private state, before any GPU work.
    names = ('receipt.json', 'endpoint.pt', 'codes.pt', 'secret.key', 'message.npy', 'reference.mp4')
    hashes = {name: digest(a.run / name) for name in names}
    os.umask(0o077)
    a.output.mkdir(parents=True, exist_ok=False)
    r = {k: source[k] for k in ('family', 'mode', 'settings', 'seed', 'case_sha256', 'method', 'mu', 'uniform_profile')}
    r['uniform_profile'] = a.uniform_profile or source['uniform_profile']
    r.update(status='starting', rows=[], fixed_target=a.fixed_target,
             model_directory=str(a.model_dir), source_sha256=digest(__file__),
             source_artifact_sha256=hashes, scope='Paired endpoint replay; no new diffusion sampling; not generation timing')
    start = time.time()

    def save():
        r['seconds'] = time.time() - start
        temp = a.output / 'receipt.tmp'
        temp.write_text(json.dumps(r, indent=2))
        temp.replace(a.output / 'receipt.json')

    save()
    try:
        import numpy as np
        import torch
        from diffusers import AutoencoderKLHunyuanVideo, AutoencoderKLWan
        from diffusers.video_processor import VideoProcessor
        from .coding import BCH512
        from .elmc import embed
        from .video import export_mp4
        torch.set_num_threads(4)
        torch.cuda.set_per_process_memory_fraction(a.memory_gib * 1024**3 / torch.cuda.get_device_properties(0).total_memory)
        z = torch.load(a.run / 'endpoint.pt', map_location='cpu', weights_only=True)
        if z.shape != (1, 16, 17, 64, 64) or not torch.isfinite(z).all():
            raise ValueError('Invalid saved endpoint')
        codes = torch.load(a.run / 'codes.pt', map_location='cpu', weights_only=True)
        bits = np.load(a.run / 'message.npy', allow_pickle=False)
        signs = BCH512().encode(bits).astype(np.float32) * 2 - 1
        cls = AutoencoderKLHunyuanVideo if source['family'] == 'hunyuan' else AutoencoderKLWan
        vae = cls.from_pretrained(a.model_dir, subfolder='vae', torch_dtype=torch.float32, local_files_only=True).to('cuda')
        vae.enable_tiling()
        with torch.inference_mode():
            marked = embed(z.cuda().float(), codes, signs, mu=source['mu'],
                           fixed_target=a.fixed_target, uniform=r['uniform_profile'])
            if source['family'] == 'hunyuan':
                latent = marked / vae.config.scaling_factor
            else:
                mean = torch.tensor(vae.config.latents_mean, device='cuda').view(1,16,1,1,1)
                std = torch.tensor(vae.config.latents_std, device='cuda').view(1,16,1,1,1)
                latent = marked * std + mean
            pixels = vae.decode(latent.float(), return_dict=False)[0]
            frames = VideoProcessor(vae_scale_factor=8).postprocess_video(pixels, output_type='pil')[0]
            r['marked_codec_command'] = export_mp4(frames, a.output / 'marked.mp4')
        for name in names:
            if digest(a.run / name) != hashes[name]:
                raise ValueError('Source changed during replay: ' + name)
        for name in ('codes.pt', 'secret.key', 'message.npy', 'reference.mp4'):
            shutil.copyfile(a.run / name, a.output / name)
            if digest(a.output / name) != hashes[name]:
                raise ValueError('Copied input mismatch: ' + name)
        r.update(status='completed', codebook_sha256=hashes['codes.pt'],
                 paired_endpoint_sha256=hashes['endpoint.pt'], marked_sha256=digest(a.output / 'marked.mp4'),
                 reference_sha256=hashes['reference.mp4'],
                 pending='Run last.evaluate and paired quality; no extraction results are implied by replay completion')
        save()
    except BaseException:
        r.update(status='failed', error=traceback.format_exc())
        save()
        raise


if __name__ == '__main__':
    main()
