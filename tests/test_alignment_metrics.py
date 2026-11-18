import pytest
from last.alignment_metrics import evaluate


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
