import hashlib
import pytest
from last.upstream import verify

def test_upstream_modification_is_detected(tmp_path):
    raw=b'original source\n';p=tmp_path/'module.py';p.write_bytes(raw)
    manifest={'commit':'example','files':[{'path':'module.py','sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}]}
    assert verify(tmp_path,manifest)['verified_files']==1
    p.write_bytes(b'modified')
    with pytest.raises(ValueError,match='changed'):verify(tmp_path,manifest)
