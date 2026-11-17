from types import SimpleNamespace
import pytest
import torch
from last.baseline_generate import denormalize_endpoint


def test_wan_channelwise_normalization_roundtrip():
    mean=torch.linspace(-2,2,16).reshape(1,16,1,1,1)
    std=torch.linspace(.5,3,16).reshape(1,16,1,1,1)
    raw=torch.arange(16*3*2*2,dtype=torch.float32).reshape(1,16,3,2,2)/20
    normalized=(raw-mean)/std
    config=SimpleNamespace(latents_mean=mean.flatten().tolist(),latents_std=std.flatten().tolist())
    assert torch.allclose(denormalize_endpoint(normalized,config,'wan22'),raw,atol=1e-6)
    with pytest.raises(ValueError,match='16-channel'):
        denormalize_endpoint(normalized[:,:8],config,'wan22')


def test_hunyuan_uses_scalar_scaling_not_wan_statistics():
    original=torch.tensor([[[[[2.,-3.]]]]])
    config=SimpleNamespace(scaling_factor=.476986)
    assert torch.allclose(denormalize_endpoint(original*config.scaling_factor,config,'hunyuan'),original)
    with pytest.raises(ValueError,match='Unknown'):
        denormalize_endpoint(original,config,'unknown')
