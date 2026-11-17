import pytest
from last.baseline_evaluate import check_extraction


def test_reused_native_extraction_requires_matching_video_and_state():
    record=dict(status='completed_extraction',method='videoshield',mode='i2v',video_sha256='video',state_sha256='state',temporal=False)
    check_extraction(record,'videoshield','i2v','video','state',False)
    for key,value in [('state_sha256','other'),('video_sha256','other'),('temporal',True),('status','failed')]:
        with pytest.raises(ValueError):check_extraction(dict(record,**{key:value}),'videoshield','i2v','video','state',False)
