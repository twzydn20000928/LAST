import pytest
from last.timing_summary import summarize
from last.temporal import attack_map
from last.timing_summary import check_drop_frames

def row(name,times):
    return dict(video_id=name,status='completed',protocol='supplement',warmups=2,repeats=5,
                seconds=times,family='hunyuan',mode='i2v',method='last',condition='clean',gpu='L40')

def test_video_medians_not_pooled_repeats():
    a=row('a',[1,1,1,100,100]);b=row('b',[2,2,9,9,9])
    result=summarize([a,b],['a','b'],100)
    assert result['median_seconds']==5  # pooled repeat median would be 5.5
    assert [r['median_seconds'] for r in result['per_video']]==[1,9]
    assert result['bootstrap']['unit']=='video'
    assert summarize([a],['a','b'])['median_seconds'] is None
    assert summarize([a],['a'])['median_ci95_seconds'] is None

def test_reject_mixed_or_duplicate_measurements():
    a=row('a',[1]*5);b=row('b',[2]*5)
    with pytest.raises(ValueError,match='duplicate'):summarize([a,a],['a','b'])
    b['condition']='drop'
    with pytest.raises(ValueError,match='Mixed'):summarize([a,b],['a','b'])
    a['warmups']=0
    with pytest.raises(ValueError,match='warmups'):summarize([a],['a'])

def test_reject_mixed_or_undeclared_generation_modes():
    a=row('a',[1]*5);b=row('b',[2]*5)
    b['mode']='t2v'
    with pytest.raises(ValueError,match='Mixed'):summarize([a,b],['a','b'])
    del a['mode']
    with pytest.raises(ValueError,match='declare'):summarize([a],['a'])


def test_drop_timing_requires_the_same_surviving_frames():
    video = "paper-000"
    drop = attack_map(video, "drop", seed=0)
    check_drop_frames({"frames": 35, "attack_map": drop}, video)
    for other in (attack_map(video, "clip"), attack_map(video, "drop", seed=1), drop[::-1]):
        assert len(other) == len(drop) == 35
        with pytest.raises(ValueError, match="surviving frames"):
            check_drop_frames({"frames": 35, "attack_map": other}, video)
    with pytest.raises(ValueError, match="surviving frames"):
        check_drop_frames({"frames": 36, "attack_map": drop}, video)
