import json
from pathlib import Path
from last.campaign import make_plan

def test_primary_matrix_and_shared_identity():
    m=json.loads((Path(__file__).resolve().parents[1]/'configs/primary_manifest.json').read_text())
    p=make_plan(m,'hash');assert len(p['runs'])==3200
    assert len({r['run'] for r in p['runs']})==3200
    selected=[r for r in p['runs'] if r['video_id']=='paper-000']
    assert len(selected)==8 and {r['key_slot'] for r in selected}=={0}
