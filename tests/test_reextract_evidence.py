import json
import numpy as np
import pytest
from last.reextract_evidence import sha, verified_rows
from last.report import aggregate


def fixture(tmp_path):
    run=tmp_path/'run'; output=tmp_path/'readout'; source=tmp_path/'source'
    (run/'attacks').mkdir(parents=True);output.mkdir();(source/'src/last').mkdir(parents=True)
    def write(path, obj):path.write_text(json.dumps(obj))
    (run/'marked.mp4').write_bytes(b'video')
    write(run/'receipt.json',dict(status='completed',method='last',family='hunyuan',mode='i2v',marked_sha256=sha(run/'marked.mp4')))
    prior=dict(condition='clean',video_id='x',status='completed',correct_bits=500,total_bits=512,exact_message=False,source_sha256=sha(run/'marked.mp4'))
    write(run/'attacks/clean.json',prior);np.save(run/'message.npy',np.zeros(512,dtype=np.uint8))
    write(output/'clean-private.json',dict(video_sha256=sha(run/'marked.mp4'),information_bits=512,message_hex='00'*64,bch_success=True,route='ccta'))
    hashes={}
    for name in ('extract.py','reextract.py','ccta.py','coding.py'):
        p=source/'src/last'/name;p.write_text('# fixture');hashes[name]=sha(p)
    row=dict(status='completed',condition='clean',received_sha256=sha(run/'marked.mp4'),prior_receipt_sha256=sha(run/'attacks/clean.json'),private_prediction_sha256=sha(output/'clean-private.json'),correct_bits=512,total_bits=512,exact_message=True,prior_correct_bits=500,same_correct_bit_count=False,bch_success=True,route='ccta')
    write(output/'receipt.json',dict(status='completed',generation_receipt_sha256=sha(run/'receipt.json'),source_sha256=hashes,conditions=['clean'],rows=[row]))
    return run,output,source


def test_explicit_reextraction_uses_new_counts_and_retains_old(tmp_path):
    run,output,source=fixture(tmp_path)
    old=(run/'attacks/clean.json').read_bytes()
    item=dict(family='hunyuan',mode='i2v',method='last',video_id='x',run='run')
    plan=dict(scope='test',runs=[item]);index={'run':dict(output=str(output),source=str(source))}
    result=aggregate(plan,tmp_path,True,index)
    clean=next(c for c in result['cells'] if c['condition']=='clean')
    assert clean['correct_bits']==512 and result['audited_observations'][0]['prior_correct_bits']==500
    assert not result['complete'] and (run/'attacks/clean.json').read_bytes()==old
    with pytest.raises(ValueError,match='verification'):aggregate(plan,tmp_path,False,index)
    with pytest.raises(ValueError,match='unplanned'):aggregate(plan,tmp_path,True,{'bad':index['run']})


@pytest.mark.parametrize('target',['video','generation','prior','prediction','source','counts','truth'])
def test_reextraction_tampering_rejected(tmp_path,target):
    run,output,source=fixture(tmp_path)
    paths={'video':run/'marked.mp4','generation':run/'receipt.json','prior':run/'attacks/clean.json','prediction':output/'clean-private.json','source':source/'src/last/ccta.py'}
    if target in paths:paths[target].write_bytes(b'changed')
    elif target=='truth':np.save(run/'message.npy',np.ones(512,dtype=np.uint8))
    else:
        p=output/'receipt.json';r=json.loads(p.read_text());r['rows'][0]['correct_bits']=511;p.write_text(json.dumps(r))
    with pytest.raises(ValueError):verified_rows(run,output,source)
