"""Stream 64 distinct wrong-key projections over already acquired features.

No video or message labels are inferred here. The caller must audit the feature
acquisition and supply every real key from the frozen development/test registry.
"""
import hashlib
import secrets
import numpy as np
from .carriers import group_code, DIMENSION
from .energy_calibration import projected_energy


def validate_keys(wrong_keys, real_keys):
    wrong_keys, real_keys = tuple(wrong_keys), tuple(real_keys)
    if (len(wrong_keys) != 64 or not real_keys
            or any(type(k) is not bytes or len(k) != 32 for k in wrong_keys+real_keys)):
        raise ValueError('Require64 wrong256-bit keys and a nonempty real-key exclusion registry')
    if len(set(wrong_keys)) != 64:
        raise ValueError('Wrong keys must be distinct')
    if set(wrong_keys) & set(real_keys):
        raise ValueError('A proposed wrong key is a real watermark key')
    return wrong_keys


def new_wrong_keys(real_keys):
    real_keys = tuple(real_keys)
    if not real_keys or any(type(k) is not bytes or len(k) != 32 for k in real_keys):
        raise ValueError('Supply the frozen real-key exclusion registry')
    chosen=[]; excluded=set(real_keys)
    while len(chosen)<64:
        key=secrets.token_bytes(32)
        if key not in excluded:
            chosen.append(key);excluded.add(key)
    return validate_keys(chosen,real_keys)


def responses(features, wrong_keys, real_keys):
    """Return candidate x64x16 energies; one group codebook resident at a time."""
    real_keys=tuple(real_keys)
    keys=validate_keys(wrong_keys,real_keys)
    values=np.asarray(features,dtype=np.float32)
    if (values.ndim!=2 or values.shape[1]!=DIMENSION or values.shape[0]==0
            or not np.isfinite(values).all()):
        raise ValueError('Expected finite nonempty candidate x1776 normalized features')
    output=np.empty((len(values),64,16),dtype=np.float64)
    for index,key in enumerate(keys):
        for group in range(16):
            code=group_code(key,group)
            output[:,index,group]=projected_energy(values@code.T)
    evidence=dict(wrong_key_sha256=[hashlib.sha256(k).hexdigest() for k in keys],
                  excluded_real_key_sha256=sorted({hashlib.sha256(k).hexdigest() for k in real_keys}),
                  candidate_count=len(values),wrong_keys=64,groups=16,
                  projection='float32 NumPy matmul; mean absolute592correlations accumulated in float64',
                  scope='Wrong-key response computation only; feature/video provenance and development calibration are separate')
    return output,evidence
