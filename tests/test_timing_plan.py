from collections import Counter
import pytest
from last.timing_plan import make_plan,METHODS


def test_timing_schedule_complete_balanced_and_repeatable():
    ids=[f'case-{i}' for i in range(30)]
    plan=make_plan(ids)
    assert plan==make_plan(ids)
    assert plan!=make_plan(ids,1)
    rows=plan['reader_jobs']
    assert len(rows)==300
    assert {(r['video_id'],r['method'],r['condition']) for r in rows}=={(i,m,c) for i in ids for m in METHODS for c in ('clean','drop')}
    assert all(r['warmups']==2 and r['repeats']==5 for r in rows)
    pairs=plan['generation_pairs']
    assert len(pairs)==150
    assert all(r['warmup_pairs']==2 and r['measured_pairs']==5 for r in pairs)
    for m in METHODS:
        assert Counter(r['order'] for r in pairs if r['method']==m)=={'AB':15,'BA':15}
        assert {r['video_id'] for r in pairs if r['method']==m}==set(ids)


def test_rejects_duplicate_timing_cases():
    with pytest.raises(ValueError):make_plan(['same']*30)
