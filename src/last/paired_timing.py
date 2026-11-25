"""Synchronized paired acquisition, shared by generation timing adapters.

Adapters must load models/keys outside this function and implement the complete
generation+decode operation inside each branch. This is not a standalone GPU
runner and does not estimate generation latency from historical receipts.
"""
import math
import statistics
import time


def checked_measured_pairs(receipt, repeats):
    measurement = receipt['measurement']
    pairs = measurement['pairs']
    if measurement['warmup_pairs'] != 2 or measurement['measured_pairs'] != repeats or len(pairs) != repeats:
        raise ValueError(f'Require two warmup pairs and {repeats} measured pairs')
    order = receipt['order']
    if (order not in ('AB', 'BA') or measurement['order'] != order
            or any(p['warmup'] is not False or p['order'] != order for p in pairs)
            or [p['pair_index'] for p in pairs] != list(range(2, 2 + repeats))):
        raise ValueError('Invalid measured generation pair order')
    return pairs


def measure_pairs(reference, marked, synchronize, guard, *, order,
                  warmup_pairs=2, measured_pairs=5, clock=time.perf_counter,
                  on_pair=None):
    if order not in ('AB', 'BA'):
        raise ValueError('Pair order must be AB or BA')
    if warmup_pairs < 1 or measured_pairs < 1:
        raise ValueError('Positive warmup and measured pair counts required')
    branches = [('reference', reference), ('marked', marked)]
    if order == 'BA':
        branches.reverse()
    records = []
    for pair_index in range(warmup_pairs + measured_pairs):
        measured = pair_index >= warmup_pairs
        durations = {}
        for name, operation in branches:
            guard()
            synchronize()
            start = clock()
            operation()
            synchronize()
            duration = clock() - start
            guard()
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Nonfinite or nonpositive duration')
            durations[name] = duration
        row = dict(pair_index=pair_index, warmup=not measured, order=order,
                   reference_seconds=durations['reference'],
                   marked_seconds=durations['marked'],
                   overhead_seconds=durations['marked'] - durations['reference'])
        # Persist only after both synchronized branches, outside timed intervals.
        # Exceptions propagate: do not silently retry or replace slow/failing pairs.
        if on_pair is not None:
            on_pair(dict(row))
        if measured:
            records.append(row)
    return dict(warmup_pairs=warmup_pairs, measured_pairs=measured_pairs,
                order=order, pairs=records,
                mean_overhead_seconds=statistics.mean(r['overhead_seconds'] for r in records),
                median_overhead_seconds=statistics.median(r['overhead_seconds'] for r in records),
                mean_marked_seconds=statistics.mean(r['marked_seconds'] for r in records),
                median_marked_seconds=statistics.median(r['marked_seconds'] for r in records))
