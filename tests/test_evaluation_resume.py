import pytest
from last.evaluate import evaluation_directory,check_cached,verify_received


def test_received_video_integrity_before_reuse(tmp_path):
    import hashlib
    video=tmp_path/'received.mp4';video.write_bytes(b'original video')
    row={'received_sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
    verify_received(row,video)
    with pytest.raises(ValueError):verify_received({},video)
    video.write_bytes(b'changed video')
    with pytest.raises(ValueError):verify_received(row,video)
    video.unlink()
    with pytest.raises(ValueError):verify_received(row,video)

def test_repeated_maps_do_not_overwrite_primary(tmp_path):
    assert evaluation_directory(tmp_path,0)==tmp_path/'attacks'
    assert evaluation_directory(tmp_path,1)==tmp_path/'attacks-map-1'
    with pytest.raises(ValueError):evaluation_directory(tmp_path,5)
    row=dict(video_id='x',method='last',source_sha256='hash')
    check_cached(row,'x','last','hash',0)
    with pytest.raises(ValueError):check_cached(row,'x','last','hash',1)
    with pytest.raises(ValueError):check_cached(row,'x','lfg','hash',0)
    with pytest.raises(ValueError):check_cached(row,'x','last','changed',0)
