import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile

import pytest


spec = importlib.util.spec_from_file_location('mmcv_builder', Path(__file__).resolve().parents[1] / 'tools/build_mmcv201.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_corrupt_source_rejected_before_extraction(tmp_path):
    with pytest.raises(ValueError, match='checksum'):
        builder.prepare(b'corrupt', tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_links_rejected_even_with_matching_checksum(tmp_path, monkeypatch):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo('mmcv-2.0.1/link')
        info.type = tarfile.SYMTYPE
        info.linkname = '/outside'
        tar.addfile(info)
    data = buffer.getvalue()
    monkeypatch.setattr(builder, 'SHA256', hashlib.sha256(data).hexdigest())
    with pytest.raises(ValueError, match='Unsafe'):
        builder.prepare(data, tmp_path)
    assert not (tmp_path / 'mmcv-2.0.1').exists()


def test_patch_changes_flags_only(tmp_path, monkeypatch):
    original = b"flags=['-std=c++14', '/std:c++14']; other=42\n"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo('mmcv-2.0.1/setup.py')
        info.size = len(original)
        tar.addfile(info, io.BytesIO(original))
    data = buffer.getvalue()
    monkeypatch.setattr(builder, 'SHA256', hashlib.sha256(data).hexdigest())
    source, hashes = builder.prepare(data, tmp_path)
    assert (source / 'setup.py').read_bytes() == original.replace(b'c++14', b'c++17')
    assert hashes['original_setup_sha256'] == hashlib.sha256(original).hexdigest()
    assert (tmp_path / 'cpp17.patch').is_file()
