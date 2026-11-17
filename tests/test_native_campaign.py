import copy,json
from collections import Counter
from pathlib import Path
import pytest
from last.native_campaign import make_plan,validate_plan,commands_for

def manifest():
    return json.loads((Path(__file__).resolve().parents[1]/'configs/primary_manifest.json').read_text())

def test_complete_native_matrix_and_shared_ids():
    p=make_plan(manifest(),'hash')
    assert len(p['runs'])==len({x['run'] for x in p['runs']})==4800
    assert set(Counter((x['family'],x['mode'],x['method']) for x in p['runs']).values())=={400}
    assert len([x for x in p['runs'] if x['video_id']=='paper-000'])==12
    validate_plan(p,manifest(),'hash')
    bad=copy.deepcopy(p);bad['runs'].pop()
    with pytest.raises(ValueError):validate_plan(bad,manifest(),'hash')
    bad=copy.deepcopy(p);bad['runs'][0]['key_slot']=7
    with pytest.raises(ValueError):validate_plan(bad,manifest(),'hash')

@pytest.mark.parametrize('method',['sigmark','videoshield','videomark'])
def test_commands_preserve_family_registry_and_blind_evaluation(tmp_path,method):
    item=dict(family='wan22',mode='i2v',method=method,video_id='paper-000')
    generate,evaluate=commands_for(item,tmp_path/'case',tmp_path/'video',tmp_path/'state','model','upstream',8)
    assert generate[generate.index('--family')+1]=='wan22'
    assert ('--registry' in generate)==(method=='videomark')
    if method=='videomark':assert generate[generate.index('--registry')+1]==str(tmp_path/'state/messages')
    assert '--message' not in evaluate and '--key' not in evaluate
    assert evaluate[evaluate.index('--video-id')+1]=='paper-000'

