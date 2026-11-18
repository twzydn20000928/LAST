import json
from pathlib import Path
import pytest
from last.campaign import make_plan, save_job

def test_primary_matrix_and_shared_identity():
    m=json.loads((Path(__file__).resolve().parents[1]/'configs/primary_manifest.json').read_text())
    p=make_plan(m,'hash');assert len(p['runs'])==3200
    assert len({r['run'] for r in p['runs']})==3200
    selected=[r for r in p['runs'] if r['video_id']=='paper-000']
    assert len(selected)==8 and {r['key_slot'] for r in selected}=={0}

def test_interrupted_receipt_update_preserves_previous_stage(tmp_path, monkeypatch):
    receipt = tmp_path/'campaign.json'
    save_job(receipt, {'status': 'running'})
    def interrupt(path, data):
        path.write_bytes(b'{')
        raise OSError('interrupted write')
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'write_text', interrupt)
        with pytest.raises(OSError, match='interrupted write'):
            save_job(receipt, {'status': 'completed'})
    assert json.loads(receipt.read_bytes()) == {'status': 'running'}
    save_job(receipt, {'status': 'completed'})
    assert json.loads(receipt.read_bytes()) == {'status': 'completed'}
