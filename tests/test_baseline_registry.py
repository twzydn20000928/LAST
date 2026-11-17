import numpy as np
import pytest
from last.baseline_generate import registered_messages

def test_native_registry_is_not_singleton_answer(tmp_path):
    shape=[1,8,1,8,8]
    (tmp_path/'a.bin').write_bytes(bytes(64))
    with pytest.raises(ValueError,match='multi-message'):registered_messages(tmp_path,shape)
    (tmp_path/'b.bin').write_bytes(bytes([255])*64)
    entries=registered_messages(tmp_path,shape)
    assert len(entries)==2 and entries[0].shape==(8,1,8,8)
    assert np.all(entries[0]==0) and np.all(entries[1]==1)
    (tmp_path/'b.bin').write_bytes(bytes(64))
    with pytest.raises(ValueError,match='Duplicate'):registered_messages(tmp_path,shape)
