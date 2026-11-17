import json
import pytest
from last.null_cache import read_keys, acquire


@pytest.mark.parametrize('value', [[], {}, ['00'], ['x'*64], ['00'*32]*2])
def test_malformed_or_duplicate_registry_rejected(tmp_path, value):
    path=tmp_path/'keys.json';path.write_text(json.dumps(value))
    with pytest.raises(ValueError):read_keys(path)


def test_real_key_overlap_rejected_before_acquisition(tmp_path):
    wrong=tmp_path/'wrong.json';real=tmp_path/'real.json'
    keys=[i.to_bytes(32,'big').hex() for i in range(64)]
    wrong.write_text(json.dumps(keys));real.write_text(json.dumps([keys[3]]))
    with pytest.raises(ValueError,match='real watermark'):
        acquire(tmp_path/'no-cache',tmp_path/'no-video',wrong,real,tmp_path/'out')
    assert not (tmp_path/'out').exists()
