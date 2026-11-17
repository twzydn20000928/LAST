import base64,hashlib
import pytest
from last.package_audit import audit


def test_source_modification_and_unsafe_record(tmp_path):
    info=tmp_path/'example-1.dist-info';info.mkdir();source=tmp_path/'example.py';source.write_bytes(b'original')
    digest=base64.urlsafe_b64encode(hashlib.sha256(source.read_bytes()).digest()).decode().rstrip('=')
    record=info/'RECORD';record.write_text(f'example.py,sha256={digest},8\n')
    assert audit(info)['changed']==[]
    source.write_bytes(b'changed');assert audit(info)['changed'][0]['path']=='example.py'
    source.unlink();assert audit(info)['missing']==['example.py']
    record.write_text('../outside.py,,\n')
    with pytest.raises(ValueError):audit(info)
