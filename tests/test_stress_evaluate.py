import hashlib,json
import pytest
from last.stress_evaluate import verify_attack
from last.stress_evaluate import verify_completed

def test_stress_verifier_rejects_replaced_video_and_wrong_source(tmp_path):
    video=tmp_path/'received.mp4';video.write_bytes(b'fixture')
    row=dict(status='completed_attack_export',source_sha256='source',received_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (tmp_path/'attack.json').write_text(json.dumps(row))
    assert verify_attack(tmp_path,'source')[1]==video
    with pytest.raises(ValueError,match='source mismatch'):verify_attack(tmp_path,'other')
    video.write_bytes(b'replaced')
    with pytest.raises(ValueError,match='changed'):verify_attack(tmp_path,'source')


def test_cached_result_binds_private_output_inputs_and_source(tmp_path):
    decoded=tmp_path/'prediction.json';decoded.write_bytes(b'private fixture')
    inputs={'video':'video-hash','key':'key-hash','vae':'model-hash'}
    sources={'extract.py':'source-hash'}
    record=dict(status='completed',input_sha256=inputs,source_sha256_files=sources,
                decoded_sha256=hashlib.sha256(decoded.read_bytes()).hexdigest())
    verify_completed(record,inputs,sources,decoded)
    for changed in ({**inputs,'key':'other'},{**inputs,'vae':'other'}):
        with pytest.raises(ValueError,match='provenance'):
            verify_completed(record,changed,sources,decoded)
    with pytest.raises(ValueError,match='provenance'):
        verify_completed(record,inputs,{'extract.py':'changed'},decoded)
    decoded.write_bytes(b'replaced')
    with pytest.raises(ValueError,match='prediction changed'):
        verify_completed(record,inputs,sources,decoded)


def test_legacy_completed_receipt_is_not_silently_reused(tmp_path):
    with pytest.raises(ValueError,match='new output directory'):
        verify_completed({'status':'completed'},{'video':'hash'},{'extract.py':'hash'},tmp_path/'absent')
