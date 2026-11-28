import json
import numpy as np
import pytest
import torch
from last.feature_cache import load,sha
from last.evaluate import candidate_features,extract,reader_nodes


def test_feature_acquisition_reuses_exact_reader_windows(capsys):
    frames=list(range(9));nodes=reader_nodes(frames,'received')
    cache={tuple(n['indices']):torch.arange(1776,dtype=torch.float32)+i for i,n in enumerate(nodes)}
    values,actual=candidate_features(frames,None,None,'hunyuan','received',False,cache)
    assert actual==nodes and torch.equal(values,torch.stack(list(cache.values())))
    codes=torch.zeros((2,592,1776));codes[:,:,0]=1
    soft,_=extract(frames,None,None,'hunyuan',codes,'received',False,cache,progress=True)
    assert torch.equal(soft,torch.ones(592))
    assert capsys.readouterr().err.splitlines() == ["Reading window 1/2", "Reading window 2/2"]


@pytest.mark.parametrize('tamper',[None,'video','features.npy','nodes.json'])
def test_cache_binds_features_to_original_video(tmp_path,tamper):
    video=tmp_path/'video.mp4';video.write_bytes(b'original')
    np.save(tmp_path/'features.npy',np.zeros((1,1776),np.float32))
    (tmp_path/'nodes.json').write_text(json.dumps([dict(start=1,end=4,segment=0,indices=[1,2,3,4])]))
    record=dict(status='completed',video_sha256=sha(video),files_sha256={n:sha(tmp_path/n) for n in ('features.npy','nodes.json')})
    (tmp_path/'receipt.json').write_text(json.dumps(record))
    if tamper:
        (video if tamper=='video' else tmp_path/tamper).write_bytes(b'changed')
        with pytest.raises(ValueError):load(tmp_path,video)
    else:
        features,nodes,_=load(tmp_path,video)
        assert features.shape==(1,1776) and len(nodes)==1
