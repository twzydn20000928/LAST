import json
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
