"""Independently re-extract existing LAST MP4s without changing old receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
from .report import CONDITIONS


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reader_command(video, key, family, model, output):
    # Neither ground truth nor attack maps are arguments to the reader.
    return [sys.executable, '-m', 'last.extract', '--video', str(video),
            '--key', str(key), '--family', family, '--model-dir', str(model),
            '--output', str(output)]


def compare(decoded, truth, prior, video_sha):
    if decoded.get('video_sha256') != video_sha:
        raise ValueError('Reader used a different video')
    if decoded.get('information_bits') != 512:
        raise ValueError('Expected 512 information bits')
    payload = bytes.fromhex(decoded['message_hex'])
    truth = np.asarray(truth)
    if len(payload) != 64 or truth.shape != (512,) or not np.isin(truth, [0, 1]).all():
        raise ValueError('Invalid prediction or truth shape/bits')
    prediction = np.unpackbits(np.frombuffer(payload, dtype=np.uint8), bitorder='big')
    correct = int((prediction == truth).sum())
    old = prior.get('correct_bits') if prior.get('status') == 'completed' else None
    return dict(correct_bits=correct, total_bits=512, exact_message=correct == 512,
                prior_correct_bits=old, same_correct_bit_count=correct == old if old is not None else None,
                bch_success=decoded['bch_success'], route=decoded['route'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--model-dir', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--conditions', nargs='+', choices=CONDITIONS, default=list(CONDITIONS))
    a = p.parse_args()
    os.umask(0o077)
    a.run = a.run.resolve(); a.output = a.output.resolve()
    generation = json.loads((a.run/'receipt.json').read_text())
    if generation.get('status') != 'completed' or generation.get('method') != 'last':
        raise ValueError('Require completed LAST generation')
    if len(set(a.conditions)) != len(a.conditions):
        raise ValueError('Duplicate conditions')
    a.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}
    record = dict(status='running', scope='Independent re-extraction, not historical bitwise parity or OS sandbox',
                  generation_receipt_sha256=digest(a.run/'receipt.json'), source_sha256=source,
                  conditions=a.conditions, rows=[])

    def save():
        temp = a.output/'receipt.tmp'
        temp.write_text(json.dumps(record, indent=2)); temp.replace(a.output/'receipt.json')

    save()
    try:
        for condition in a.conditions:
            video = a.run/'marked.mp4' if condition == 'clean' else a.run/'attacks'/(condition+'.mp4')
            prior_path = a.run/'attacks'/(condition+'.json')
            prior = json.loads(prior_path.read_text())
            if prior.get('condition') != condition:
                raise ValueError('Prior condition mismatch')
            video_sha = digest(video); prior_sha = digest(prior_path)
            private = a.output/(condition+'-private.json')
            started = time.monotonic()
            command = reader_command(video, a.run/'secret.key', generation['family'], a.model_dir, private)
            with (a.output/(condition+'.log')).open('wb') as log:
                subprocess.run(command, cwd=a.output, stdout=log, stderr=subprocess.STDOUT, check=True)
            if digest(video) != video_sha or digest(prior_path) != prior_sha:
                raise ValueError('Input changed during re-extraction')
            # Evaluation truth is loaded only after the separate reader has exited.
            decoded = json.loads(private.read_text())
            counts = compare(decoded, np.load(a.run/'message.npy'), prior, video_sha)
            row = dict(status='completed', condition=condition, received_sha256=video_sha,
                       prior_receipt_sha256=prior_sha, private_prediction_sha256=digest(private),
                       seconds=time.monotonic()-started, **counts)
            record['rows'].append(row); save()
            print(json.dumps(row), flush=True)
        if source != {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}:
            raise ValueError('Reader source changed during audit')
        record['status'] = 'completed'; save()
    except BaseException:
        record.update(status='failed', error=traceback.format_exc()); save(); raise


if __name__ == '__main__':
    main()
