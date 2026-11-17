import json
import hashlib
import pytest
from last.report import aggregate,CONDITIONS

def test_missing_failure_and_duplicate_are_not_hidden(tmp_path):
    item=dict(family='hunyuan',mode='i2v',method='last',video_id='x',run='run')
    plan=dict(scope='test',runs=[item]);attacks=tmp_path/'run/attacks';attacks.mkdir(parents=True)
    for name in CONDITIONS[:-1]:
        row=dict(video_id='x',condition=name,status='completed',correct_bits=512,total_bits=512,exact_message=True)
        (attacks/(name+'.json')).write_text(json.dumps(row))
    report=aggregate(plan,tmp_path)
    assert not report['complete']
    missing=next(r for r in report['cells'] if r['condition']=='clip')
    assert missing['missing']==1 and missing['final_bit_accuracy'] is None
    (attacks/'clip.json').write_text(json.dumps(dict(video_id='x',condition='clip',status='failed')))
    assert next(r for r in aggregate(plan,tmp_path)['cells'] if r['condition']=='clip')['failed']==1
    with pytest.raises(ValueError,match='Duplicate'):aggregate(dict(scope='test',runs=[item,item]),tmp_path)

def test_artifact_audit_rejects_stale_source_and_missing_attack(tmp_path):
    item=dict(family='hunyuan',mode='i2v',method='last',video_id='x',run='run')
    plan=dict(scope='audit',runs=[item]);folder=tmp_path/'run';(folder/'attacks').mkdir(parents=True)
    (folder/'marked.mp4').write_bytes(b'source fixture')
    (folder/'receipt.json').write_text(json.dumps(dict(status='completed',family='hunyuan',mode='i2v',method='last')))
    row=dict(video_id='x',method='last',condition='clean',status='completed',correct_bits=500,total_bits=512,exact_message=False,source_sha256='stale')
    target=folder/'attacks/clean.json';target.write_text(json.dumps(row))
    with pytest.raises(ValueError,match='different source'):aggregate(plan,tmp_path,True)
    row['source_sha256']=hashlib.sha256((folder/'marked.mp4').read_bytes()).hexdigest()
    row['received_sha256']=row['source_sha256'];target.write_text(json.dumps(row))
    result=aggregate(plan,tmp_path,True)
    assert len(result['audited_observations'])==1 and not result['complete']
    row['condition']='noise';(folder/'attacks/noise.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='video missing'):aggregate(plan,tmp_path,True)
    (folder/'attacks/noise.mp4').write_bytes(b'original attacked video')
    row['received_sha256']=hashlib.sha256((folder/'attacks/noise.mp4').read_bytes()).hexdigest()
    (folder/'attacks/noise.json').write_text(json.dumps(row))
    assert len(aggregate(plan,tmp_path,True)['audited_observations'])==2
    (folder/'attacks/noise.mp4').write_bytes(b'replaced attacked video')
    with pytest.raises(ValueError,match='received-video hash'):aggregate(plan,tmp_path,True)
    del row['received_sha256']
    (folder/'attacks/noise.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='received-video hash'):aggregate(plan,tmp_path,True)

def test_plan_cannot_escape_root(tmp_path):
    item=dict(family='hunyuan',mode='i2v',method='last',video_id='x',run='../outside')
    with pytest.raises(ValueError,match='escapes'):aggregate(dict(scope='test',runs=[item]),tmp_path)
