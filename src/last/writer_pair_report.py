"""Audit one equal-margin endpoint intervention; never extrapolate to a benchmark."""
import argparse
import hashlib
import json
from pathlib import Path

CONDITIONS = ('clean', 'noise', 'compression', 'blur', 'drop', 'insert', 'clip')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def report(minimum, fixed):
    minimum, fixed = Path(minimum), Path(fixed)
    left, right = read(minimum/'receipt.json'), read(fixed/'receipt.json')
    if any(r.get('status') != 'completed' or r.get('method') != 'last' for r in (left, right)):
        raise ValueError('Both generations must be completed LAST runs')
    if left.get('fixed_target') is not False or right.get('fixed_target') is not True:
        raise ValueError('Require minimum-margin and fixed-target interventions')
    for field in ('family', 'mode', 'settings', 'seed', 'case_sha256', 'mu', 'uniform_profile'):
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
    maps = {}; identity = None; quality_definition = None
    for name, folder, generation in [('minimum-margin', minimum, left), ('fixed-target', fixed, right)]:
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
            signature = (row.get('map_seed'), row.get('attack_map'), row.get('frames'))
            if name == 'minimum-margin': maps[condition] = signature
            elif maps[condition] != signature: raise ValueError('Paired temporal maps differ')
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
    for name in ('minimum', 'fixed', 'output'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): p.error('Output exists; preserve previous audit')
    value = report(a.minimum, a.fixed)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(value, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
