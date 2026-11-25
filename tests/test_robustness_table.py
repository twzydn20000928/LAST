from copy import deepcopy
import pytest
from last.robustness_table import collect,render
from last.report import CONDITIONS


def sample():
    return dict(artifact_verification=True,cells=[dict(family='hunyuan',mode='i2v',method='last',condition=c,
                expected=400,completed=2,correct_bits=862,total_bits=1024,exact_messages=0,
                complete=False,observed_bit_accuracy=0,final_bit_accuracy=None) for c in CONDITIONS])


def test_transposed_table_recomputes_counts_and_keeps_partial_coverage():
    text,counts=render(collect([sample()]))
    assert text.count('84.18% [partial]; 2/400')==7
    assert len(counts)==7 and all(r['exact_messages']==0 and r['final_bit_accuracy'] is None for r in counts)


def test_overlap_and_invalid_final_or_missing_conditions_rejected():
    with pytest.raises(ValueError,match='Overlapping'):collect([sample(),sample()])
    bad=sample();bad['cells'][0]['final_bit_accuracy']=.9
    with pytest.raises(ValueError,match='Partial'):collect([bad])
    missing=sample();missing['cells'].pop()
    with pytest.raises(ValueError,match='seven'):collect([missing])


def test_impossible_exact_counts_and_unaudited_input_rejected():
    bad=sample();bad['cells'][0]['correct_bits']=1023
    with pytest.raises(ValueError,match='incorrect bit'):collect([bad])
    bad=sample();bad['cells'][0]['exact_messages']=2
    with pytest.raises(ValueError):collect([bad])
    bad=sample();bad['artifact_verification']=False
    with pytest.raises(ValueError):collect([bad])


@pytest.mark.parametrize("plan_field", ["planned_videos_per_method", "planned_videos"])
def test_complete_prefix_remains_partial_in_full_benchmark_table(plan_field):
    report = sample()
    report[plan_field] = 400
    for row in report['cells']:
        row.update(expected=2, complete=True, final_bit_accuracy=862/1024)
    text, counts = render(collect([report]))
    assert text.count('84.18% [partial]; 2/400') == 7
    assert all(r['final_bit_accuracy'] is None for r in counts)
    report[plan_field] = 1
    with pytest.raises(ValueError, match='smaller'):
        collect([report])
