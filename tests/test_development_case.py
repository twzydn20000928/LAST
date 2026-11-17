import hashlib,json
import pytest
from last.development_case import build


def test_replicates_share_verified_image_but_keep_own_seed(tmp_path):
    manifest={'samples':[dict(id=f'dev-{i}',prompt='p',seed=i,key_slot=i) for i in range(4)]}
    image=tmp_path/'input.png';image.write_bytes(b'fixture')
    receipt=dict(status='completed',manifest_sha256='manifest',sample_id='dev-0',seed=0,prompt='p',image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    (tmp_path/'receipt.json').write_text(json.dumps(receipt))
    case=build(manifest,'dev-3','i2v','manifest',tmp_path)
    assert case['seed']==3 and case['image']==str(image.resolve())
    assert 'image' not in build(manifest,'dev-3','t2v','manifest')
    with pytest.raises(ValueError):build(manifest,'dev-3','i2v','different',tmp_path)
    image.write_bytes(b'changed')
    with pytest.raises(ValueError):build(manifest,'dev-3','i2v','manifest',tmp_path)
