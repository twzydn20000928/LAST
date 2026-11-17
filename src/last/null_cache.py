"""Persist private wrong-key responses tied to an audited candidate cache.

This is acquisition, not development fitting or an authentication experiment.
The supplied real-key registry must contain every actual development/test key.
"""
import argparse
import json
import os
import time
import traceback
from pathlib import Path

import numpy as np
from .feature_cache import load, sha
from .null_energy import new_wrong_keys, responses, validate_keys


def read_keys(path):
    values = json.loads(Path(path).read_text())
    if (not isinstance(values, list) or not values
            or any(not isinstance(x, str) or len(x) != 64 for x in values)):
        raise ValueError('Key file must be a nonempty JSON list of 64-character hexadecimal keys')
    keys = tuple(bytes.fromhex(x) for x in values)
    if any(len(k) != 32 for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('Key registry contains malformed or duplicate keys')
    return keys


def acquire(cache, video, wrong_keys, real_keys, output):
    cache, video, wrong_keys, real_keys, output = map(Path, (cache, video, wrong_keys, real_keys, output))
    os.umask(0o077)
    wrong, real = read_keys(wrong_keys), read_keys(real_keys)
    validate_keys(wrong, real)
    values, nodes, feature_record = load(cache, video)
    inputs = {str(p.resolve()): sha(p) for p in
              (video, wrong_keys, real_keys, cache/'receipt.json', cache/'features.npy', cache/'nodes.json')}
    source = Path(__file__).parent
    sources = {name: sha(source/name) for name in
               ('null_cache.py', 'null_energy.py', 'energy_calibration.py', 'carriers.py', 'feature_cache.py')}
    output.mkdir(parents=True, exist_ok=False)
    record = dict(status='running', input_sha256=inputs, source_sha256=sources,
                  video_sha256=feature_record['video_sha256'], candidates=len(nodes),
                  scope='Actual wrong-key responses only; no development membership or complete registry claim')
    started = time.monotonic()
    def save():
        record['seconds'] = time.monotonic()-started
        temp = output/'receipt.tmp'
        temp.write_text(json.dumps(record, indent=2))
        temp.replace(output/'receipt.json')
    save()
    try:
        energies, evidence = responses(values, wrong, real)
        if any(sha(Path(p)) != digest for p, digest in inputs.items()):
            raise ValueError('Input artifact or key registry changed during response acquisition')
        if any(sha(source/name) != digest for name, digest in sources.items()):
            raise ValueError('Response implementation changed during acquisition')
        np.save(output/'energies.npy', energies, allow_pickle=False)
        record.update(status='completed', evidence=evidence,
                      energies_sha256=sha(output/'energies.npy'), shape=list(energies.shape))
        save()
        return record
    except BaseException:
        record.update(status='failed', error=traceback.format_exc())
        save()
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init-keys')
    init.add_argument('--real-keys', type=Path, required=True)
    init.add_argument('--output', type=Path, required=True)
    run = commands.add_parser('acquire')
    for name in ('cache', 'video', 'wrong-keys', 'real-keys', 'output'):
        run.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    os.umask(0o077)
    if a.command == 'init-keys':
        keys = new_wrong_keys(read_keys(a.real_keys))
        with a.output.open('x') as f:
            json.dump([k.hex() for k in keys], f)
        print('Created private64-key bank; keep it for replay, do not publish it.')
    else:
        result = acquire(a.cache, a.video, a.wrong_keys, a.real_keys, a.output)
        print(json.dumps(dict(status=result['status'], candidates=result['candidates'])))


if __name__ == '__main__':
    main()
