"""Post-hoc matched-hypothesis statistics for supplement Table 13.

No candidate search, calibration fitting, or message decoding occurs here.
The caller must supply matched correct/wrong scores from the frozen protocol.
"""
import numpy as np


def clean_energy_pairs(correlations, calibration):
    """Use the same windows and consecutive group assignments as the consistency row."""
    from .energy_calibration import projected_energy, transform

    if np.shape(correlations) != (16, 16, 592):
        raise ValueError("Expected 16 clean windows x 16 group hypotheses x 592 coefficients")
    median = calibration.get("pooled_wrong_key_median")
    if median is None or not np.isfinite(median) or median <= 0:
        raise ValueError("Recompute a positive pooled wrong-key median from development responses")
    energy = projected_energy(correlations)
    calibrated = transform(energy, calibration)
    pairs = []
    offsets = np.arange(4)
    for start in range(13):
        windows = start + offsets
        raw = [float(energy[windows, j + offsets].mean() / median) for j in range(13)]
        adjusted = [float(calibrated[windows, j + offsets].mean()) for j in range(13)]
        for j in range(13):
            if j != start:
                pairs.append(dict(window_start=start, wrong_group_start=j,
                                  raw_correct=raw[start], raw_wrong=raw[j],
                                  calibrated_correct=adjusted[start], calibrated_wrong=adjusted[j]))
    return pairs


def clean_consistency_pairs(correlations):
    """Pair group assignments on the same four clean windows in source order.

    Axis order is observed group, hypothesized group, BCH coefficient.
    Callers must bind this array to a clean-video receipt and verified frame order.
    """
    values = np.asarray(correlations)
    if values.shape != (16, 16, 592) or not np.isfinite(values).all():
        raise ValueError("Expected 16 clean windows x 16 group hypotheses x 592 coefficients")
    offsets = np.arange(4)
    pairs = []
    for start in range(13):
        windows = start + offsets
        correct = four_group_consistency(values[windows, windows])
        for alternative in range(13):
            if alternative == start:
                continue
            wrong = four_group_consistency(values[windows, alternative + offsets])
            pairs.append(dict(window_start=start, wrong_group_start=alternative,
                              correct=correct, wrong=wrong))
    return pairs


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
