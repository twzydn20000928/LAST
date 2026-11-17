import hashlib,json
import pytest
from last.stress_evaluate import verify_attack

def test_stress_verifier_rejects_replaced_video_and_wrong_source(tmp_path):
    video=tmp_path/'received.mp4';video.write_bytes(b'fixture')
    row=dict(status='completed_attack_export',source_sha256='source',received_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (tmp_path/'attack.json').write_text(json.dumps(row))
    assert verify_attack(tmp_path,'source')[1]==video
    with pytest.raises(ValueError,match='source mismatch'):verify_attack(tmp_path,'other')
    video.write_bytes(b'replaced')
    with pytest.raises(ValueError,match='changed'):verify_attack(tmp_path,'source')
