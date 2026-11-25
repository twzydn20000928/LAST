import pytest
from last.quality_report import aggregate, CATEGORIES
from last.quality_report import build
import hashlib
import json


def test_merge_prior_dimension_requires_identical_scored_subset(tmp_path):
    name = 'Composition'
    original, current, scores = (tmp_path / s for s in ('original', 'current', 'scores'))
    for path in (original, current, scores):
        path.mkdir()
    video = '/videos/sample.mp4'
    coverage = dict(complete=False, family='hunyuan', mode='i2v', method='last',
                    manifest_sha256='a'*64, videos=[dict(path=video, sha256='b'*64)])
    metadata = json.dumps([dict(video_list=[video])])
    for folder in (original, current):
        (folder / (name+'.json')).write_text(metadata)
    old = original/'coverage.json'
    old.write_text(json.dumps(coverage))
    coverage['videos'].append(dict(path='/videos/later.mp4', sha256='c'*64))
    (current/'coverage.json').write_text(json.dumps(coverage))
    receipt = dict(status='completed', dimension=name, mean=0.5,
                   videos_sha256={video:'b'*64}, coverage_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
                   metadata_sha256=hashlib.sha256(metadata.encode()).hexdigest())
    (scores/'receipt.json').write_text(json.dumps(receipt))
    (scores/'official_result.json').write_text(json.dumps([0.5,[dict(video_path=video,video_results=0.5)]]))
    previous = [(name, original, scores)]
    assert build(current, tmp_path, previous)['dimensions'][name]['mean'] == 0.5
    coverage['videos'][0]['sha256'] = 'd'*64
    (current/'coverage.json').write_text(json.dumps(coverage))
    with pytest.raises(ValueError, match='Prior dimension videos differ'):
        build(current, tmp_path, previous)


def test_five_categories_are_equally_weighted_not_eighteen_dimensions():
    rows={d:dict(status='completed',mean=0) for ds in CATEGORIES.values() for d in ds}
    for d in CATEGORIES['Creativity']: rows[d]['mean']=1
    assert aggregate(rows,True)['v_score']==pytest.approx(.2)
    assert aggregate(rows,False)['v_score'] is None
    rows['Diversity']['full_dimension_inputs'] = False
    partial = aggregate(rows, True)
    assert partial['categories']['Creativity'] is None
    assert partial['categories']['Commonsense'] == 0
    assert partial['v_score'] is None
    del rows['Diversity']['full_dimension_inputs']
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
    dimension = build(tmp_path,tmp_path)['dimensions'][name]
    assert dimension['mean'] == 0.8
    assert dimension['full_dimension_inputs'] is False
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


def test_two_dimensions_cannot_count_the_same_sample(tmp_path):
    video = '/runs/paper-000/marked.mp4'
    coverage = dict(complete=False, family='hunyuan', mode='i2v', method='last',
                    videos=[dict(path=video, sha256='a'*64)])
    (tmp_path/'coverage.json').write_text(json.dumps(coverage))
    for name in ('Composition', 'Camera_Motion'):
        metadata = tmp_path/(name+'.json')
        metadata.write_text(json.dumps([{'video_list': [video]}]))
        folder = tmp_path/name
        folder.mkdir()
        state = dict(dimension=name, status='completed', mean=1,
                     metadata_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest(),
                     videos_sha256={video: 'a'*64})
        (folder/'receipt.json').write_text(json.dumps(state))
        (folder/'official_result.json').write_text(json.dumps(
            [1, [dict(video_path=video, video_results=1)]]))
    with pytest.raises(ValueError, match='assigned more than once'):
        build(tmp_path, tmp_path)
