import pytest
from last.timing_summary import summarize
from last.temporal import attack_map
from last.timing_summary import check_drop_frames
from last.timing_summary import check_timed_frames


def test_timed_length_for_native_warmups_and_measured_reads():
    native = dict(method="sigmark", warmups=2, repeats=5,
                  diagnostics_including_warmups=[{"received_frames": 35} for _ in range(7)])
    check_timed_frames(native, 35)
    native["diagnostics_including_warmups"][0]["received_frames"] = 65
    with pytest.raises(ValueError, match="input length"):
        check_timed_frames(native, 35)
    with pytest.raises(ValueError, match="frame count"):
        check_timed_frames({"method": "last", "frames": 35}, 65)

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


def test_protocol_variants_cannot_enter_standard_extraction_cell():
    sample = row('a', [1]*5)
    sample['length_study_frames'] = 129
    with pytest.raises(ValueError, match='Length-study'):
        summarize([sample], ['a'])
    sample.update(method='sigmark', length_study_frames=None, temporal=True)
    with pytest.raises(ValueError, match='temporal recovery'):
        summarize([sample], ['a'])
    sample['condition'] = 'drop'
    assert summarize([sample], ['a'])['complete']
    sample['temporal'] = False
    with pytest.raises(ValueError, match='temporal recovery'):
        summarize([sample], ['a'])
