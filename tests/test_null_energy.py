import numpy as np
import pytest
from last.null_energy import validate_keys,new_wrong_keys,responses


def keys():return tuple(i.to_bytes(32,'big') for i in range(64))


def test_duplicate_correct_and_missing_exclusions_rejected():
    real=[(100).to_bytes(32,'big')]
    assert validate_keys(keys(),real)==keys()
    with pytest.raises(ValueError,match='distinct'):validate_keys(keys()[:-1]+keys()[:1],real)
    with pytest.raises(ValueError,match='real watermark'):validate_keys(keys(),[keys()[0]])
    with pytest.raises(ValueError):validate_keys(keys(),[])
    with pytest.raises(ValueError):validate_keys(keys()[:63],real)
    generated=new_wrong_keys(real)
    assert len(set(generated))==64 and not set(generated)&set(real)


def test_projection_indexes_every_key_and_group(monkeypatch):
    # This isolates streaming/indexing; actual QR construction is tested separately.
    calls=[]
    def small_code(key,group):
        calls.append((key,group))
        code=np.zeros((592,1776),np.float32)
        code[:,group]=1
        return code
    monkeypatch.setattr('last.null_energy.group_code',small_code)
    features=np.zeros((1,1776),np.float32);features[0,:16]=np.arange(16)
    result,evidence=responses(features,keys(),[(100).to_bytes(32,'big')])
    assert result.shape==(1,64,16) and np.array_equal(result[0],np.tile(np.arange(16),(64,1)))
    assert len(calls)==64*16 and len(set(calls))==len(calls)
    assert len(evidence['wrong_key_sha256'])==64


def test_invalid_features_fail_before_projection():
    for values in (np.zeros((0,1776)),np.zeros((1,592)),np.full((1,1776),np.nan)):
        with pytest.raises(ValueError):responses(values,keys(),[(100).to_bytes(32,'big')])
