import numpy as np
import pytest
from last.hypothesis_statistics import clean_consistency_pairs, four_group_consistency, matched_summary


def test_matched_chains_keep_windows_fixed_and_never_wrap():
    values = np.zeros((16, 16, 592))
    for window in range(16):
        values[window, :, window] = 1
        values[window, window] = 1
    rows = clean_consistency_pairs(values)
    assert {(r['window_start'], r['wrong_group_start']) for r in rows} == {
        (i, j) for i in range(13) for j in range(13) if i != j}
    assert len(rows) == 156
    assert all(r['correct'] == pytest.approx(1) and r['wrong'] == 0 for r in rows)


def test_fixed_four_pairwise_cosines():
    rows = np.tile([1., 2., -1.], (4, 1))
    assert four_group_consistency(rows * np.arange(1, 5)[:, None]) == pytest.approx(1.)
    assert four_group_consistency(np.eye(4)) == pytest.approx(0.)
    rows = np.array([[1., 0.], [1., 0.], [-1., 0.], [-1., 0.]])
    assert four_group_consistency(rows) == pytest.approx(-1 / 3)
    for invalid in (np.zeros((4, 2)), np.ones((3, 2)), np.full((4, 2), np.nan)):
        with pytest.raises(ValueError):
            four_group_consistency(invalid)


def test_roc_auc_is_not_matched_pair_win_rate():
    # Every paired comparison wins, but one negative outranks another positive.
    result = matched_summary([2., 4.], [1., 3.], ['a', 'b'], ['a', 'b'])
    assert result['auroc'] == .75
    assert result['correct'] == dict(p05=2.1, median=3., p95=3.9)
    assert matched_summary([1., 1.], [1., 1.], ['a', 'b'], ['a', 'b'])['auroc'] == .5
    assert matched_summary([0., 0.], [1., 1.], ['a', 'b'], ['a', 'b'])['auroc'] == 0.


def test_reject_unmatched_and_invalid_scores():
    for positive, negative, a, b in [
        ([1., 2.], [0., 1.], ['a', 'b'], ['b', 'a']),
        ([1., 2.], [0., 1.], ['a', 'a'], ['a', 'a']),
        ([], [], [], []),
        ([float('nan')], [0.], ['a'], ['a']),
        ([1.], [0., 1.], ['a'], ['a']),
    ]:
        with pytest.raises(ValueError):
            matched_summary(positive, negative, a, b)
