"""Verify independent readout evidence without rewriting historical receipts."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_rows(run, output, source):
    import numpy as np
    from .reextract import compare
    run, output, source = map(Path, (run, output, source))
    receipt = output/'receipt.json'
    record = json.loads(receipt.read_text())
    if record.get('status') != 'completed':
        raise ValueError('Re-extraction evidence is not complete')
    if record.get('generation_receipt_sha256') != sha(run/'receipt.json'):
        raise ValueError('Re-extraction generation receipt changed')
    generation = json.loads((run/'receipt.json').read_text())
    marked = sha(run/'marked.mp4')
    if generation.get('method') != 'last' or generation.get('marked_sha256') != marked:
        raise ValueError('Re-extraction source video differs from LAST generation')
    hashes = record.get('source_sha256', {})
    if not {'extract.py', 'reextract.py', 'ccta.py', 'coding.py'} <= hashes.keys():
        raise ValueError('Incomplete re-extraction source evidence')
    for name, digest in hashes.items():
        if Path(name).name != name or sha(source/'src/last'/name) != digest:
            raise ValueError('Re-extraction source differs from supplied checkout')
    conditions = record.get('conditions', [])
    rows = record.get('rows', [])
    if (not conditions or len(set(conditions)) != len(conditions)
            or len(rows) != len(conditions) or {r['condition'] for r in rows} != set(conditions)):
        raise ValueError('Incomplete or duplicate re-extraction conditions')
    verified = {}
    for row in rows:
        condition = row['condition']
        if condition not in ('clean', 'noise', 'compression', 'blur', 'drop', 'insert', 'clip'):
            raise ValueError('Unknown re-extraction condition')
        video = run/'marked.mp4' if condition == 'clean' else run/'attacks'/(condition+'.mp4')
        prior_path = run/'attacks'/(condition+'.json')
        decoded_path = output/(condition+'-private.json')
        if (row.get('status') != 'completed' or sha(video) != row.get('received_sha256')
                or sha(prior_path) != row.get('prior_receipt_sha256')
                or sha(decoded_path) != row.get('private_prediction_sha256')):
            raise ValueError('Re-extraction video, prior receipt or prediction changed')
        prior = json.loads(prior_path.read_text())
        if prior.get('condition') != condition or prior.get('source_sha256') != marked:
            raise ValueError('Historical receipt refers to another source or condition')
        counts = compare(json.loads(decoded_path.read_text()), np.load(run/'message.npy'), prior, sha(video))
        if any(row.get(k) != v for k, v in counts.items()):
            raise ValueError('Re-extraction counts differ from actual decoded message')
        verified[condition] = dict(counts, received_sha256=sha(video), status='completed',
                                   reextraction_receipt_sha256=sha(receipt),
                                   reextraction_source_sha256=hashes)
    return verified
