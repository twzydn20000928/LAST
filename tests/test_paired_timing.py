import pytest
from last.paired_timing import checked_measured_pairs, measure_pairs


def test_main_table_rejects_duplicate_pair_and_wrong_branch_order():
    clock = iter(range(16))
    noop = lambda: None
    measurement = measure_pairs(noop, noop, noop, noop, order='BA', measured_pairs=2,
                                clock=lambda: next(clock))
    receipt = dict(order='BA', measurement=measurement)
    first, second = checked_measured_pairs(receipt, 2)
    second['pair_index'] = first['pair_index']
    with pytest.raises(ValueError, match='pair order'):
        checked_measured_pairs(receipt, 2)
    second.update(pair_index=3, order='AB')
    with pytest.raises(ValueError, match='pair order'):
        checked_measured_pairs(receipt, 2)


def test_pair_order_warmup_exclusion_and_negative_overhead():
    events = []
    persisted = []
    # One warmup and two measured BA pairs. A slow warmup must not contribute.
    times = iter([0, 100, 100, 101, 101, 104, 104, 109, 109, 116, 116, 120])
    result = measure_pairs(lambda: events.append('A'), lambda: events.append('B'),
        lambda: events.append('sync'), lambda: events.append('guard'),
        order='BA', warmup_pairs=1, measured_pairs=2, clock=lambda: next(times),
        on_pair=persisted.append)
    assert [x for x in events if x in ('A', 'B')] == ['B', 'A'] * 3
    assert events[:5] == ['guard', 'sync', 'B', 'sync', 'guard']
    assert len(persisted) == 3 and persisted[0]['warmup']
    assert [r['overhead_seconds'] for r in result['pairs']] == [-2, 3]
    assert result['median_overhead_seconds'] == .5
    assert result['mean_marked_seconds'] == 5


def test_partial_pair_failure_is_not_retried_or_recorded_as_success():
    calls = []
    saved = []
    def fail():
        calls.append('marked')
        raise RuntimeError('GPU failure')
    with pytest.raises(RuntimeError, match='GPU failure'):
        measure_pairs(lambda: calls.append('reference'), fail, lambda: None,
                      lambda: None, order='AB', on_pair=saved.append)
    assert calls == ['reference', 'marked'] and not saved


def test_contention_stops_before_operation():
    calls = []
    def guard():
        raise RuntimeError('Other GPU process')
    with pytest.raises(RuntimeError, match='Other GPU process'):
        measure_pairs(lambda: calls.append('A'), lambda: calls.append('B'),
                      lambda: None, guard, order='AB')
    assert not calls
