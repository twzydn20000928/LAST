"""Recompute four wrong-key/group projections for every cached candidate window."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from last.carriers import group_code
from last.feature_cache import load, sha
from last.null_cache import read_keys
from last.null_energy import validate_keys


def replay(video, cache, responses, wrong_keys, real_keys):
    record = json.loads((responses / 'receipt.json').read_bytes())
    values, nodes, feature_record = load(cache, video)
    energies_file = responses / 'energies.npy'
    if (record['status'] != 'completed' or record['video_sha256'] != feature_record['video_sha256']
            or sha(energies_file) != record['energies_sha256']):
        raise ValueError('Wrong-key response receipt does not match the video or stored array')
    inputs = (video, wrong_keys, real_keys, cache / 'receipt.json', cache / 'features.npy', cache / 'nodes.json')
    for path in inputs:
        if record['input_sha256'].get(str(path.resolve())) != sha(path):
            raise ValueError('Input differs from the response acquisition receipt')
    keys = validate_keys(read_keys(wrong_keys), read_keys(real_keys))
    energies = np.load(energies_file, allow_pickle=False)
    expected = (len(nodes), 64, 16)
    if energies.shape != expected or record['shape'] != list(expected) or record['candidates'] != len(nodes):
        raise ValueError('Response dimensions differ from the candidate/key/group protocol')
    for key, group in itertools.product((0, 63), (0, 15)):
        correlations = values.astype(np.float32, copy=False) @ group_code(keys[key], group).T
        measured = np.abs(correlations).mean(axis=1, dtype=np.float64)
        np.testing.assert_allclose(measured, energies[:, key, group], rtol=1e-6, atol=1e-8)
    return dict(candidates=len(nodes), responses=energies.size, recomputed=4 * len(nodes),
                mp4_sha256=record['video_sha256'], response_receipt_sha256=sha(responses / 'receipt.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('video', 'cache', 'responses', 'wrong-keys', 'real-keys'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(json.dumps(replay(**vars(parser.parse_args())), indent=2))
