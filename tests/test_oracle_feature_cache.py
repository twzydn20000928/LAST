from types import SimpleNamespace
import pytest
import torch
from last import oracle_feature_cache as cache


class Processor:
    def __init__(self):self.inputs=[]
    def preprocess_video(self,batch):
        self.inputs.append(batch[0])
        return torch.tensor(batch[0],dtype=torch.float32)


class VAE:
    config=SimpleNamespace(scaling_factor=2)
    def encode(self,x):return SimpleNamespace(latent_dist=SimpleNamespace(mode=lambda:x))


def test_acquisition_excludes_foreign_and_duplicate_frames_and_fills_same_group(monkeypatch):
    processor=Processor()
    monkeypatch.setattr(cache,'feature',lambda z:torch.full((1776,),float(z.mean())))
    values,nodes=cache.acquire(list(range(9)),[0,4,-1,1,4,9,10,11,12],VAE(),processor,'hunyuan','cpu')
    assert processor.inputs==[[3,3,3,1,1],[5,5,6,7,8]]
    assert [n['group'] for n in nodes]==[0,2]
    assert values.shape==(2,1776)
    assert torch.allclose(values[:,0],torch.tensor([4.4,12.4]))
    # No source frame zero, foreign frame at2 or duplicate at4 contributes.
    assert all(not set(row)&{0,2,4} for row in processor.inputs)


def test_empty_oracle_evidence_and_invalid_map(monkeypatch):
    processor=Processor()
    values,nodes=cache.acquire([1,2],[-1,0],VAE(),processor,'hunyuan','cpu')
    assert values.shape==(0,1776) and nodes==[] and processor.inputs==[]
    with pytest.raises(ValueError):cache.acquire([1],[],VAE(),processor,'hunyuan','cpu')
    with pytest.raises(ValueError):cache.acquire([1],[65],VAE(),processor,'hunyuan','cpu')


def test_wan_normalization_is_applied_before_frequency_features(monkeypatch):
    class Wan:
        config=SimpleNamespace(latents_mean=[2]*16,latents_std=[4]*16)
        def encode(self,x):return SimpleNamespace(latent_dist=SimpleNamespace(mode=lambda:torch.full((1,16,2,1,1),10.)))
    captured=[]
    def feature(z):
        captured.append(z.clone());return torch.zeros(1776)
    monkeypatch.setattr(cache,'feature',feature)
    cache.acquire([1,2,3,4],[1,2,3,4],Wan(),Processor(),'wan22','cpu')
    assert torch.equal(captured[0],torch.full((1,16,2,1,1),2.))
