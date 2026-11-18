from types import SimpleNamespace
import pytest
import torch
from last.native_model_adapter import normalize_endpoint,SGOVAE,native_call_kwargs
from last.baseline_generate import denormalize_endpoint


def test_wan_roundtrip_and_sgo_normalize_exactly_once():
    config=SimpleNamespace(latents_mean=[i/10 for i in range(16)],latents_std=[.5+i/20 for i in range(16)])
    z=torch.randn(2,16,3,4,4)
    raw=denormalize_endpoint(z,config,'wan22')
    class VAE:
        dtype=torch.float32
        def encode(self,pixels):return SimpleNamespace(latent_dist=SimpleNamespace(mode=lambda:raw.clone()))
    vae=VAE();vae.config=config
    proxy=SGOVAE(vae)
    sgo=proxy.encode(None).latent_dist.mode()*proxy.config.scaling_factor
    torch.testing.assert_close(sgo,z)
    torch.testing.assert_close(sgo,normalize_endpoint(raw,config,'wan22'))
    assert vae.config is config and not hasattr(config,'scaling_factor')


def test_hunyuan_scaling_and_call_are_preserved():
    z=torch.randn(1,16,2,4,4)
    torch.testing.assert_close(normalize_endpoint(z,SimpleNamespace(scaling_factor=.5),'hunyuan'),z*.5)
    kw={'guidance_scale':6,'image':'first','num_inference_steps':50}
    assert native_call_kwargs(kw,'hunyuan','i2v')==kw
    assert 'image' not in native_call_kwargs(kw,'hunyuan','t2v')
    assert kw['image']=='first'


@pytest.mark.parametrize('mode',['i2v','t2v'])
def test_wan_experts_receive_declared_guidance(mode):
    original={'guidance_scale':6,'image':'first','num_frames':9,'num_inference_steps':50}
    kw=native_call_kwargs(original,'wan22',mode)
    assert kw['guidance_scale']==kw['guidance_scale_2']==5
    assert kw['num_frames']==9 and kw['num_inference_steps']==50
    assert ('image' in kw)==(mode=='i2v')
    assert original['guidance_scale']==6


def test_invalid_wan_normalization_is_rejected():
    with pytest.raises(ValueError,match='normalization'):
        normalize_endpoint(torch.zeros(1,16,2,2,2),SimpleNamespace(latents_mean=[0]*16,latents_std=[0]*16),'wan22')


def test_wan_single_image_container_adapter_preserves_upstream_input():
    image=object();original={'image':[image]}
    assert native_call_kwargs(original,'wan22','i2v')['image'] is image
    assert original['image']==[image]
    assert native_call_kwargs(original,'hunyuan','i2v')['image']==[image]
    for images in ([],[image,image]):
        with pytest.raises(ValueError,match='one conditioning image'):
            native_call_kwargs({'image':images},'wan22','i2v')


def test_actual_diffusers_wan_check_inputs_accepts_adapted_image():
    pytest.importorskip('diffusers')
    from diffusers import WanImageToVideoPipeline
    from PIL import Image
    image=Image.new('RGB',(512,512))
    # Exercise the real installed input validator without model weights or GPU.
    receiver=SimpleNamespace(config=SimpleNamespace(boundary_ratio=.875))
    original=dict(prompt=[''],negative_prompt=None,image=[image],height=512,width=512)
    with pytest.raises(ValueError,match='image.*type'):
        WanImageToVideoPipeline.check_inputs(receiver,**original)
    adapted=native_call_kwargs(original,'wan22','i2v')
    adapted.pop('guidance_scale')
    WanImageToVideoPipeline.check_inputs(receiver,**adapted)
