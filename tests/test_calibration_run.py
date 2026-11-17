import json
from pathlib import Path
import pytest
from last.calibration_run import conditioning_case,sha,validate_plan
from last.lfg_calibration import make_plan


def test_grid_cannot_be_shortened_or_retuned():
    root=Path(__file__).resolve().parents[1]
    dev=json.loads((root/'configs/development_manifest.json').read_text())
    primary=json.loads((root/'configs/primary_manifest.json').read_text())
    plan=make_plan(dev,primary,'lfg-c','hunyuan')
    validate_plan(plan,dev,primary)
    plan['runs']=plan['runs'][:-1]
    with pytest.raises(ValueError):validate_plan(plan,dev,primary)


def test_conditioning_is_shared_across_seeds_and_hash_checked(tmp_path):
    rows=[dict(index=i,id=f'dev-{i:03}',prompt='fixed prompt',seed=100+i,key_slot=i) for i in range(4)]
    dev={'samples':rows}
    assert conditioning_case(rows[3],dev,tmp_path) is None
    folder=tmp_path/'prompt-00';folder.mkdir();(folder/'input.png').write_bytes(b'fixed conditioning')
    receipt=dict(status='completed',prompt='fixed prompt',seed=100,image_sha256=sha(folder/'input.png'))
    (folder/'receipt.json').write_text(json.dumps(receipt))
    case=conditioning_case(rows[3],dev,tmp_path)
    assert case['seed']==103 and case['image']==str(folder/'input.png')
    (folder/'input.png').write_bytes(b'changed')
    with pytest.raises(ValueError):conditioning_case(rows[3],dev,tmp_path)
