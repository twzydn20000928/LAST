import pytest
from last.cluster_intervals import summarize

def rows(seeds=(0,)):
    return [dict(video_id=v,map_seed=s,status='completed',correct_bits=n,total_bits=512) for v,n in [('a',512),('b',256),('c',0)] for s in seeds]

def test_repeating_maps_does_not_create_independent_samples():
    clusters={'a':'p1','b':'p1','c':'p2'}
    one=summarize(rows(),clusters,draws=200)
    five=summarize(rows(range(5)),clusters,list(range(5)),draws=200)
    assert one['bit_accuracy']==five['bit_accuracy']==.5
    assert one['bit_accuracy_ci95']==five['bit_accuracy_ci95']
    assert five['prompt_clusters']==2 and five['video_map_trials']==15
    paired=summarize(rows(),clusters,paired_rows=rows(),draws=200)
    assert paired['bit_accuracy']==0 and paired['bit_accuracy_ci95']==[0,0]

def test_missing_rows_and_single_cluster_are_not_false_precision():
    clusters={'a':'p','b':'p','c':'p'}
    assert summarize(rows(),clusters,draws=100)['bit_accuracy_ci95'] is None
    with pytest.raises(ValueError,match='Missing'):summarize(rows()[:-1],clusters,draws=100)
    with pytest.raises(ValueError,match='Duplicate'):summarize(rows()+rows()[:1],clusters,draws=100)
