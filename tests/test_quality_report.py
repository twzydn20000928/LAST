import pytest
from last.quality_report import aggregate, CATEGORIES
from last.quality_report import build
import hashlib
import json


def test_five_categories_are_equally_weighted_not_eighteen_dimensions():
    rows={d:dict(status='completed',mean=0) for ds in CATEGORIES.values() for d in ds}
    for d in CATEGORIES['Creativity']: rows[d]['mean']=1
    assert aggregate(rows,True)['v_score']==pytest.approx(.2)
    assert aggregate(rows,False)['v_score'] is None
    rows['Human_Identity']['mean']=None
    result=aggregate(rows,True)
    assert result['v_score'] is None and result['missing_or_invalid_dimensions']==['Human_Identity']
    rows['Human_Identity']=dict(status='failed',mean=0)
    assert not aggregate(rows,True)['complete']


def test_replaced_video_at_same_path_invalidates_cached_score(tmp_path):
    name = 'Composition'
    folder = tmp_path / name
    folder.mkdir()
    video = '/runs/example.mp4'
    metadata = tmp_path / (name + '.json')
    metadata.write_text(json.dumps([{'video_list':[video]}]))
    coverage = dict(complete=False,family='hunyuan',mode='i2v',method='last',
                    videos=[dict(path=video,sha256='a'*64)])
    (tmp_path/'coverage.json').write_text(json.dumps(coverage))
    state = dict(dimension=name,status='completed',mean=0.8,
                 metadata_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest(),
                 videos_sha256={video:'a'*64})
    (folder/'receipt.json').write_text(json.dumps(state))
    (folder/'official_result.json').write_text(json.dumps([0.8,[dict(video_path=video,video_results=0.8)]]))
    assert build(tmp_path,tmp_path)['dimensions'][name]['mean']==0.8
    coverage['videos'][0]['sha256']='b'*64
    (tmp_path/'coverage.json').write_text(json.dumps(coverage))
    with pytest.raises(ValueError,match='hashes'):
        build(tmp_path,tmp_path)
    coverage['videos'][0]['sha256'] = 'a'*64
    manifest = tmp_path/'coverage.json'
    manifest.write_text(json.dumps(coverage))
    state['coverage_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (folder/'receipt.json').write_text(json.dumps(state))
    assert build(tmp_path,tmp_path)['method'] == 'last'
    coverage['method'] = 'lfg'
    manifest.write_text(json.dumps(coverage))
    with pytest.raises(ValueError, match='coverage manifest'):
        build(tmp_path,tmp_path)
