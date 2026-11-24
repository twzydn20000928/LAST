import pytest
from last.alignment_metrics import evaluate, stress_source_indices


def test_cross_boundary_window_cannot_be_given_a_fictitious_group():
    nodes=[dict(indices=[1,2,3,4]),dict(indices=[3,4,5,6]),dict(indices=[5,6,7,8])]
    r=evaluate(nodes,list(range(9)),[dict(candidate=0,group=0),dict(candidate=1,group=1)])
    assert r['correct']==1 and r['false_window_selected']==1
    assert r['selected_alignment_accuracy']==.5 and r['intact_only_group_accuracy']==1.
    assert r['intact_group_coverage']==.5 and r['rows'][1]['true_group'] is None


def test_foreign_padded_and_reordered_windows_are_not_intact():
    nodes=[dict(indices=[0,1,2,3]),dict(indices=[4,5,6,6]),dict(indices=[7,8,9,10])]
    mapping=[1,-1,3,4,5,6,7,12,11,10,9]
    r=evaluate(nodes,mapping,[dict(candidate=i,group=i) for i in range(3)])
    assert r['false_window_selected']==3 and r['correct']==0
    assert r['selected_alignment_accuracy']==0 and r['intact_only_group_accuracy'] is None


def test_intact_wrong_identity_and_empty_selection_are_explicit():
    nodes=[dict(indices=[0,1,2,3])]
    r=evaluate(nodes,[1,2,3,4],[dict(candidate=0,group=1)])
    assert r['wrong_group_on_intact']==1 and r['false_window_selected']==0
    assert evaluate(nodes,[1,2,3,4],[])['selected_alignment_accuracy'] is None
    with pytest.raises(ValueError):evaluate(nodes,[1,2,3,4],[dict(candidate=0,group=0)]*2)


@pytest.mark.parametrize('boundary', [0, 7, 65])
def test_donor_indices_are_foreign_even_at_clip_boundaries(boundary):
    receipt = dict(attack='natural30', frames=95, mapping=dict(boundary=boundary, donor_count=30))
    mapping = stress_source_indices(receipt)
    assert mapping[boundary:boundary+30] == [-1]*30
    assert [i for i in mapping if i >= 0] == list(range(65))


def test_synthetic_midpoints_and_exact_duplicates_have_different_truth():
    positions = list(range(30))
    midpoints = stress_source_indices(dict(attack='interpolate30', frames=95, mapping=dict(midpoint_pairs=positions)))
    assert midpoints[:4] == [0, -1, 1, -1]
    source = [j for i in range(65) for j in ([i, i] if i < 30 else [i])]
    receipt = dict(attack='duplicate30', frames=95, mapping=dict(duplicated_indices=positions, source_indices=source))
    assert stress_source_indices(receipt) == source
    receipt['mapping']['source_indices'] = midpoints
    with pytest.raises(ValueError, match='source order'):
        stress_source_indices(receipt)
