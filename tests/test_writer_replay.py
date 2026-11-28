import json
import pytest
from last.writer_replay import digest, validate_source


def test_source_replay_rejects_replaced_endpoint(tmp_path):
    r = dict(status='completed', method='last', family='hunyuan')
    for name, field in [('endpoint.pt','endpoint_sha256'), ('codes.pt','codebook_sha256'), ('marked.mp4','marked_sha256')]:
        (tmp_path / name).write_bytes(name.encode())
        r[field] = digest(tmp_path / name)
    (tmp_path / 'receipt.json').write_text(json.dumps(r))
    assert validate_source(tmp_path) == r
    (tmp_path / 'endpoint.pt').write_bytes(b'different endpoint')
    with pytest.raises(ValueError, match='endpoint.pt'):
        validate_source(tmp_path)


def test_source_replay_requires_success(tmp_path):
    (tmp_path / 'receipt.json').write_text(json.dumps(dict(status='failed', method='last')))
    with pytest.raises(ValueError, match='completed LAST'):
        validate_source(tmp_path)


@pytest.mark.parametrize("recorded", [False, True])
def test_same_decoder_can_move_but_weights_must_match(tmp_path, recorded):
    from last.models import vae_fingerprints
    from last.writer_replay import verify_replay_vae
    import shutil

    original, moved = tmp_path / 'original', tmp_path / 'moved'
    (original / 'vae').mkdir(parents=True)
    (original / 'vae/config.json').write_text('{}')
    (original / 'vae/diffusion_pytorch_model.safetensors').write_bytes(b'weights')
    shutil.copytree(original, moved)
    source = {'model_directory': str(original)}
    if recorded:
        source['vae_files_sha256'] = vae_fingerprints(original)
        original.rename(tmp_path / 'stored-elsewhere')
    verify_replay_vae(source, moved)
    (moved / 'vae/diffusion_pytorch_model.safetensors').write_bytes(b'changed')
    with pytest.raises(ValueError, match='differs'):
        verify_replay_vae(source, moved)
