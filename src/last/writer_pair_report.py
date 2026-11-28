"""Audit one equal-margin endpoint intervention; never extrapolate to a benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
from last.temporal import attack_map

CONDITIONS = ('clean', 'noise', 'compression', 'blur', 'drop', 'insert', 'clip')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def report(minimum, fixed, *, uniform_profile=False):
    minimum, fixed = Path(minimum), Path(fixed)
    left, right = read(minimum/'receipt.json'), read(fixed/'receipt.json')
    if any(r.get('status') != 'completed' or r.get('method') != 'last' for r in (left, right)):
        raise ValueError('Both generations must be completed LAST runs')
    # The original generation and replay implementations used CUDA exclusively.
    if left.get('device', 'cuda') != right.get('device', 'cuda'):
        raise ValueError('Paired writers must use the same compute device')
    expected_fixed_target = not uniform_profile
    if left.get('fixed_target') is not False or right.get('fixed_target') is not expected_fixed_target:
        raise ValueError('Writer rule differs from the requested intervention')
    if uniform_profile:
        if left.get('uniform_profile') is not False or right.get('uniform_profile') is not True:
            raise ValueError('Require nonuniform and uniform minimum-margin writers')
    elif 'uniform_profile' not in left or left['uniform_profile'] != right.get('uniform_profile'):
        raise ValueError('Paired generation settings differ: uniform_profile')
    for field in ('family', 'mode', 'settings', 'seed', 'case_sha256', 'mu'):
        if field not in left or left[field] != right.get(field):
            raise ValueError('Paired generation settings differ: '+field)
    for name in ('receipt.json', 'endpoint.pt', 'codes.pt', 'secret.key', 'message.npy', 'reference.mp4'):
        if digest(minimum/name) != right.get('source_artifact_sha256', {}).get(name):
            raise ValueError('Replay source artifact mismatch: '+name)
    for name in ('codes.pt', 'secret.key', 'message.npy', 'reference.mp4'):
        if digest(minimum/name) != digest(fixed/name):
            raise ValueError('Paired input mismatch: '+name)
    if digest(minimum/'endpoint.pt') != left.get('endpoint_sha256') or left['endpoint_sha256'] != right.get('paired_endpoint_sha256'):
        raise ValueError('Endpoint mismatch')
    result = dict(scope='One paired real endpoint, equal margin; not the full ablation set or matched-PSNR control',
                  family=left['family'], mode=left['mode'], seed=left['seed'], margin=left['mu'],
                  settings=left['settings'], variants={})
    identity = None; quality_definition = None
    labels = ('nonuniform-profile', 'uniform-profile') if uniform_profile else ('minimum-margin', 'fixed-target')
    if uniform_profile:
        result['scope'] = 'Paired temporal margin profiles on one real endpoint; same minimum-margin writer and base margin'
    for name, folder, generation in [(labels[0], minimum, left), (labels[1], fixed, right)]:
        marked = digest(folder/'marked.mp4')
        if generation.get('marked_sha256') != marked:
            raise ValueError('Marked MP4 mismatch')
        quality = read(folder/'quality.json')
        if quality.get('reference_sha256') != digest(folder/'reference.mp4') or quality.get('marked_sha256') != marked:
            raise ValueError('Quality input mismatch')
        if quality_definition is None: quality_definition = quality['definition']
        if quality['definition'] != quality_definition: raise ValueError('Quality definitions differ')
        rows = []
        for condition in CONDITIONS:
            path = folder/'attacks'/(condition+'.json'); row = read(path)
            if row.get('status') != 'completed' or row.get('condition') != condition or row.get('method') != 'last':
                raise ValueError('Incomplete or mismatched condition')
            if identity is None: identity = row['video_id']
            if row.get('video_id') != identity or row.get('source_sha256') != marked:
                raise ValueError('Attack source identity mismatch')
            received = folder/'marked.mp4' if condition == 'clean' else folder/'attacks'/(condition+'.mp4')
            if row.get('received_sha256') != digest(received): raise ValueError('Received MP4 mismatch')
            mapping = attack_map(identity, condition) if condition in ('drop', 'insert', 'clip') else None
            expected_frames = len(mapping) if mapping is not None else 65
            if (row.get('map_seed') != 0 or row['attack_map'] != mapping
                    or row.get('frames') != expected_frames):
                raise ValueError(f'Attack differs from frozen protocol for {identity}/{condition}')
            correct = row.get('correct_bits')
            if type(correct) is not int or not 0 <= correct <= 512 or row.get('total_bits') != 512:
                raise ValueError('Invalid information-bit counts')
            if row.get('exact_message') is not (correct == 512): raise ValueError('Exact-message flag mismatch')
            rows.append(dict(condition=condition, correct_bits=correct, total_bits=512,
                             bit_accuracy=correct/512, exact_message=correct == 512,
                             received_sha256=digest(received), receipt_sha256=digest(path)))
        result['variants'][name] = dict(conditions=rows, psnr_db=quality['psnr_db'], ssim=quality['ssim'],
                                       marked_sha256=marked, quality_receipt_sha256=digest(folder/'quality.json'),
                                       generation_receipt_sha256=digest(folder/'receipt.json'))
    result.update(video_id=identity, quality_definition=quality_definition,
                  reference_sha256=digest(minimum/'reference.mp4'))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('minimum', 'output'): p.add_argument('--'+name, type=Path, required=True)
    variants = p.add_mutually_exclusive_group(required=True)
    variants.add_argument('--fixed', type=Path)
    variants.add_argument('--uniform', type=Path, help='Compare temporal profiles with minimum-margin writing in both arms')
    a = p.parse_args()
    if a.output.exists(): p.error('Output exists; preserve previous audit')
    value = report(a.minimum, a.uniform or a.fixed, uniform_profile=a.uniform is not None)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(value, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
