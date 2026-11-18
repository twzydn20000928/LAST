"""Post-hoc matched-hypothesis statistics for supplement Table 13.

No candidate search, calibration fitting, or message decoding occurs here.
The caller must supply matched correct/wrong scores from the frozen protocol.
"""
import numpy as np


def four_group_consistency(rows):
    """Mean of six pairwise cosines, not the length-scaled search score."""
    rows = np.asarray(rows, dtype=np.float64)
    if rows.ndim != 2 or rows.shape[0] != 4 or rows.shape[1] == 0 or not np.isfinite(rows).all():
        raise ValueError('Require four finite, nonempty correlation vectors')
    norm = np.linalg.norm(rows, axis=1)
    # A zero projection has no cosine direction; do not invent a valid score.
    if (norm < 1e-8).any():
        raise ValueError('Undefined cosine for a negligible projection')
    unit = rows / norm[:, None]
    return float((unit @ unit.T)[np.triu_indices(4, 1)].mean())


def matched_summary(correct, wrong, correct_ids, wrong_ids):
    """P05/median/P95 and pooled ROC AUC with half credit for tied scores.

    IDs bind each pair to the same video/candidate. They must be unique and
    identically ordered. This validates matching metadata, not its provenance.
    AUROC compares all positive-negative pairs, not just paired win frequency.
    """
    positive = np.asarray(correct, dtype=np.float64)
    negative = np.asarray(wrong, dtype=np.float64)
    if (positive.ndim != 1 or negative.shape != positive.shape or positive.size == 0
            or not np.isfinite(positive).all() or not np.isfinite(negative).all()):
        raise ValueError('Require equally sized nonempty finite score arrays')
    if (len(correct_ids) != len(positive) or list(correct_ids) != list(wrong_ids)
            or any(not isinstance(x, str) or not x for x in correct_ids)
            or len(set(correct_ids)) != len(correct_ids)):
        raise ValueError('Require unique matched candidate IDs in identical order')
    # Sorted negatives allow exact tie handling without an N-by-N allocation.
    sorted_negative = np.sort(negative)
    lower = np.searchsorted(sorted_negative, positive, side='left')
    upper = np.searchsorted(sorted_negative, positive, side='right')
    auc = float((lower + .5 * (upper - lower)).sum() / (positive.size * negative.size))
    def quantiles(values):
        q = np.quantile(values, [.05, .5, .95], method='linear')
        return dict(p05=float(q[0]), median=float(q[1]), p95=float(q[2]))
    return dict(matched_pairs=int(positive.size), correct=quantiles(positive),
                wrong=quantiles(negative), auroc=auc,
                quantile_method='linear', higher_score_hypothesis='correct',
                scope='Matched hypothesis discrimination, not bit accuracy or authentication rate')
