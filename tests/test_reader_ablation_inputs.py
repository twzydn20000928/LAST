import hashlib
import json
import pytest
from last.reader_ablation import verified_attack


def fixture_run(tmp_path):
    (tmp_path/'attacks').mkdir()
    (tmp_path/'marked.mp4').write_bytes(b'original-export')
    (tmp_path/'attacks/drop.mp4').write_bytes(b'received-export')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    generation={'marked_sha256':sha(tmp_path/'marked.mp4')}
    attack={'status':'completed','condition':'drop','source_sha256':generation['marked_sha256'],
            'received_sha256':sha(tmp_path/'attacks/drop.mp4')}
    (tmp_path/'attacks/drop.json').write_text(json.dumps(attack))
    return generation,attack


def test_original_exports_accepted_and_replaced_attack_rejected(tmp_path):
    generation,_=fixture_run(tmp_path)
    _,path=verified_attack(tmp_path,'drop',generation)
    path.write_bytes(b'replaced-export')
    with pytest.raises(ValueError,match='Received MP4'):
        verified_attack(tmp_path,'drop',generation)


def test_changed_source_rejected(tmp_path):
    generation,_=fixture_run(tmp_path)
    (tmp_path/'marked.mp4').write_bytes(b'replaced-source')
    with pytest.raises(ValueError,match='Generation MP4'):
        verified_attack(tmp_path,'drop',generation)


@pytest.mark.parametrize('change',[{'condition':'insert'},{'received_sha256':None},{'status':'failed'}])
def test_wrong_or_unverified_receipt_rejected(tmp_path,change):
    generation,attack=fixture_run(tmp_path)
    attack.update(change)
    (tmp_path/'attacks/drop.json').write_text(json.dumps(attack))
    with pytest.raises(ValueError):
        verified_attack(tmp_path,'drop',generation)

