"""Warm-model LAST/LFG extraction timing on an otherwise idle single GPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time


def compute_pids(text):
    return {int(line.strip()) for line in text.splitlines() if line.strip()}


def require_exclusive():
    pids = compute_pids(subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], text=True))
    other = pids - {os.getpid()}
    if other:
        raise RuntimeError(f'Timing requires exclusive GPU; other compute PIDs: {sorted(other)}')


def measure(operation, synchronize, guard, warmups, repeats, clock=time.perf_counter, after_warmup=None):
    if warmups < 1 or repeats < 1:
        raise ValueError('Positive warmup and repeat counts required')
    for _ in range(warmups):
        guard(); operation(); synchronize(); guard()
    if after_warmup is not None:
        after_warmup()
    durations = []
    for _ in range(repeats):
        guard(); synchronize(); started = clock()
        operation(); synchronize(); elapsed = clock()-started
        guard()
        if elapsed <= 0:
            raise ValueError('Nonpositive duration')
        durations.append(elapsed)
    return durations


def verify_prediction(path, video_sha, family, bits, method='last'):
    import numpy as np
    expected = json.loads(path.read_bytes())
    if (expected.get('method', 'last') != method or expected.get('video_sha256') != video_sha or expected.get('family') != family
            or expected.get('information_bits') != 512
            or bytes.fromhex(expected['message_hex']) != np.packbits(bits, bitorder='big').tobytes()):
        raise ValueError('Final timed prediction differs from the supplied ordinary extraction')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video', type=Path, required=True)
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--model-dir', required=True)
    p.add_argument('--family', choices=['hunyuan', 'wan22'], required=True)
    p.add_argument('--mode', choices=['i2v', 't2v'], required=True)
    p.add_argument('--method', choices=['last', 'lfg'], required=True)
    p.add_argument('--protocol', choices=['main', 'supplement'], required=True)
    p.add_argument('--length-study-frames', type=int, choices=(65,129,257),
                   help='Supplement LAST clean extraction length, checked against the decoded MP4')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-extraction', type=Path,
                   help='Compare the final timed prediction with a private last.extract JSON after timing')
    a = p.parse_args()
    if a.length_study_frames is not None and (a.protocol != 'supplement' or a.method != 'last'):
        p.error('--length-study-frames requires LAST and the supplement timing protocol')
    os.umask(0o077)
    if a.output.exists():
        raise ValueError('Use a new output file')
    require_exclusive()  # Never terminate another workload or time through contention.
    import numpy as np
    import torch
    from diffusers import AutoencoderKLHunyuanVideo, AutoencoderKLWan
    from diffusers.video_processor import VideoProcessor
    from .carriers import codebook
    from .coding import BCH512
    from .evaluate import extract, extract_lfg
    from .video import load_mp4
    torch.set_num_threads(4)
    key = a.key.read_bytes()
    if len(key) != 32:
        raise ValueError('Expected 32-byte key')
    codes = torch.from_numpy(codebook(key)) if a.method == 'last' else None
    prepared = None
    if a.method == 'lfg':
        from .lfg import carriers
        prepared = [carriers(key, p).to(device='cuda', dtype=torch.float32) for p in range(8)]
    codec = BCH512()
    cls = AutoencoderKLHunyuanVideo if a.family == 'hunyuan' else AutoencoderKLWan
    vae = cls.from_pretrained(a.model_dir, subfolder='vae', torch_dtype=torch.float32, local_files_only=True).to('cuda')
    vae.enable_tiling()
    processor = VideoProcessor(vae_scale_factor=8)
    sha = hashlib.sha256(a.video.read_bytes()).hexdigest()
    source = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')}
    last_read = {}
    final_bits = None
    if a.length_study_frames is not None and len(load_mp4(a.video)) != a.length_study_frames:
        raise ValueError('Input MP4 frame count differs from requested length study')

    def operation():
        nonlocal final_bits
        frames = load_mp4(a.video)  # MP4 decoding belongs inside the timed region.
        if not frames or any(np.asarray(f).shape != (512, 512, 3) for f in frames):
            raise ValueError('Expected nonempty 512-square RGB video')
        with torch.inference_mode():
            if a.method == 'last':
                soft, alignment = extract(frames, vae, processor, a.family, codes)
            else:
                soft, alignment = extract_lfg(frames, vae, processor, a.family, key, prepared)
            final_bits, decoder = codec.decode(soft.cpu().numpy())
        last_read.update(frames=len(frames), route=alignment['route'], bch_success=decoder['bch_success'])
        if a.method == 'last':
            last_read['candidate_windows'] = alignment['candidate_windows']

    repeats = 2 if a.protocol == 'main' else 5
    times = measure(operation, torch.cuda.synchronize, require_exclusive, 2, repeats,
                    after_warmup=torch.cuda.reset_peak_memory_stats)
    peak_allocated_bytes = torch.cuda.max_memory_allocated()
    if hashlib.sha256(a.video.read_bytes()).hexdigest() != sha:
        raise ValueError('Video changed during timing')
    if source != {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')}:
        raise ValueError('Source changed during timing')
    if a.expected_extraction:
        verify_prediction(a.expected_extraction, sha, a.family, final_bits, a.method)
        last_read['final_prediction_matches_ordinary_extraction'] = True
    result = dict(status='completed', method=a.method, family=a.family, mode=a.mode, protocol=a.protocol,
                  scope='One-video warm-model extraction only; not generation overhead or the full timing table',
                  received_sha256=sha, source_sha256=source, warmups=2, repeats=repeats,
                  seconds=times, mean_seconds=statistics.mean(times), median_seconds=statistics.median(times),
                  reported_seconds=statistics.mean(times) if a.protocol=='main' else statistics.median(times),
                  includes=['MP4 decoding', 'complete reader', 'BCH decoding'],
                  excludes=['model loading', 'one-time key/codebook setup', 'export'],
                  concurrency_check='No other compute PID before/after every repetition; not an OS reservation',
                  gpu=torch.cuda.get_device_name(0), torch_version=torch.__version__, cuda_version=torch.version.cuda,
                  peak_allocated_bytes=peak_allocated_bytes, length_study_frames=a.length_study_frames,
                  **last_read)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(dict(status='completed', reported_seconds=result['reported_seconds'])))


if __name__ == '__main__':
    main()
