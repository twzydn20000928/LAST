import pytest
from last.evaluate import evaluation_directory,check_cached

def test_repeated_maps_do_not_overwrite_primary(tmp_path):
    assert evaluation_directory(tmp_path,0)==tmp_path/'attacks'
    assert evaluation_directory(tmp_path,1)==tmp_path/'attacks-map-1'
    with pytest.raises(ValueError):evaluation_directory(tmp_path,5)
    row=dict(video_id='x',method='last',source_sha256='hash')
    check_cached(row,'x','last','hash',0)
    with pytest.raises(ValueError):check_cached(row,'x','last','hash',1)
    with pytest.raises(ValueError):check_cached(row,'x','lfg','hash',0)
    with pytest.raises(ValueError):check_cached(row,'x','last','changed',0)
