"""Explicit reconstruction of development-only wrong-key energy calibration.

The supplement specifies 64 wrong keys but not the transform. This module uses
per-group median and 1.4826*MAD. It is not the primary raw-energy fallback.
"""
import numpy as np
from .development import validate_development

DEFINITION = 'mean absolute correlation; per-group pooled development median and 1.4826*MAD; floor1e-8'


def projected_energy(correlations):
    values = np.asarray(correlations, dtype=np.float64)
    if values.ndim < 2 or values.shape[-1] != 592 or not np.isfinite(values).all():
        raise ValueError('Expected finite correlations for 592 code bits')
    return np.abs(values).mean(axis=-1)


def fit(wrong_key_energy, video_ids, development, primary):
    """Fit only on all80 development videos; 64 null responses per candidate.

    Input shape: candidate x wrong-key x group. Every candidate contributes
    equally; no messages, correctness labels, test scores or attack maps enter.
    Generation/feature provenance must be audited by the acquisition caller.
    """
    validate_development(development, primary)
    values = np.asarray(wrong_key_energy, dtype=np.float64)
    if (values.ndim != 3 or values.shape[1:] != (64, 16)
            or values.shape[0] != len(video_ids) or not np.isfinite(values).all()
            or (values < 0).any()):
        raise ValueError('Expected nonnegative finite candidate x64x16 wrong-key energies')
    expected = {r['id'] for r in development['samples']}
    if set(video_ids) != expected:
        raise ValueError('Require all80 development IDs and no test or extra IDs')
    pooled = values.reshape(-1,16)
    center = np.median(pooled,axis=0)
    raw_scale = 1.4826*np.median(np.abs(pooled-center),axis=0)
    return dict(schema_version=1, definition=DEFINITION, reconstruction=True,
                scope='Development fitted energy transform; acquisition provenance and real-video validation required',
                wrong_keys_per_candidate=64, groups=16, candidates=len(video_ids),
                pooled_wrong_key_median=float(np.median(pooled)),
                videos=sorted(expected), center=center.tolist(),
                scale=np.maximum(raw_scale,1e-8).tolist(),
                degenerate_groups=np.flatnonzero(raw_scale<1e-8).tolist())


def transform(energies, calibration):
    """Apply frozen development statistics without refitting on received video."""
    if (calibration.get('schema_version') != 1 or calibration.get('definition') != DEFINITION
            or calibration.get('wrong_keys_per_candidate') != 64
            or calibration.get('groups') != 16):
        raise ValueError('Incompatible energy calibration')
    values = np.asarray(energies,dtype=np.float64)
    center = np.asarray(calibration['center'],dtype=np.float64)
    scale = np.asarray(calibration['scale'],dtype=np.float64)
    if (values.ndim < 1 or values.shape[-1] != 16 or not np.isfinite(values).all()
            or (values<0).any() or center.shape != (16,) or scale.shape != (16,)
            or not np.isfinite(center).all() or not np.isfinite(scale).all()
            or (center<0).any() or (scale<1e-8).any()):
        raise ValueError('Invalid energy inputs or frozen calibration statistics')
    return (values-center)/scale
