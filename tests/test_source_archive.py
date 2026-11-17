import zipfile
import pytest
from last.source_archive import unpack,digest


def test_pinned_archive_extraction_and_traversal_rejection(tmp_path):
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('root/LICENSE','upstream license')
    manifest=dict(sha256=digest(archive),archive_root='root',repository='owner/repo',commit='fixed')
    receipt=unpack(archive,tmp_path/'source',manifest)
    assert (tmp_path/'source/LICENSE').read_text()=='upstream license'
    assert receipt['files']['LICENSE']==digest(tmp_path/'source/LICENSE')
    with zipfile.ZipFile(archive,'w') as z:z.writestr('root/../outside','bad')
    manifest['sha256']=digest(archive)
    with pytest.raises(ValueError):unpack(archive,tmp_path/'unsafe',manifest)
    assert not (tmp_path/'unsafe').exists()
