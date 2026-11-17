import pytest
from last.baseline_evaluate import check_extraction


def test_reused_native_extraction_requires_matching_video_and_state():
    record=dict(status='completed_extraction',method='videoshield',mode='i2v',family='hunyuan',video_sha256='video',state_sha256='state',temporal=False)
    check_extraction(record,'videoshield','i2v','video','state',False)
    for key,value in [('state_sha256','other'),('video_sha256','other'),('temporal',True),('status','failed')]:
        with pytest.raises(ValueError):check_extraction(dict(record,**{key:value}),'videoshield','i2v','video','state',False)


@pytest.mark.parametrize('family',['hunyuan','wan22'])
def test_native_reuse_cannot_cross_model_families(family):
    record=dict(status='completed_extraction',method='videomark',mode='i2v',family=family,
                video_sha256='same-video',state_sha256='same-state',temporal=True)
    check_extraction(record,'videomark','i2v','same-video','same-state',True,family)
    other='wan22' if family=='hunyuan' else 'hunyuan'
    with pytest.raises(ValueError):
        check_extraction(record,'videomark','i2v','same-video','same-state',True,other)
    del record['family']
    with pytest.raises(ValueError):
        check_extraction(record,'videomark','i2v','same-video','same-state',True,family)

