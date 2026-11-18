"""Explicit model normalization bridge for upstream native SGO.

The upstream algorithm and its PRC detector are not modified. Wan normalization
replaces Hunyuan's scalar scaling only at the SGO VAE boundary.
"""
from types import SimpleNamespace
import torch


def load_inversion_pipeline(model_dir, family, mode, scheduler_cls):
    from diffusers import (AutoencoderKLHunyuanVideo, AutoencoderKLWan,
                           HunyuanVideoImageToVideoPipeline, HunyuanVideoPipeline,
                           WanImageToVideoPipeline, WanPipeline)
    vae_cls, pipeline_cls, shift = {
        ('hunyuan', 'i2v'): (AutoencoderKLHunyuanVideo, HunyuanVideoImageToVideoPipeline, 7),
        ('hunyuan', 't2v'): (AutoencoderKLHunyuanVideo, HunyuanVideoPipeline, 7),
        ('wan22', 'i2v'): (AutoencoderKLWan, WanImageToVideoPipeline, 5),
        ('wan22', 't2v'): (AutoencoderKLWan, WanPipeline, 5),
    }[family, mode]
    vae = vae_cls.from_pretrained(model_dir, subfolder='vae', torch_dtype=torch.float32, local_files_only=True)
    vae.enable_tiling()
    pipe = pipeline_cls.from_pretrained(model_dir, vae=vae, torch_dtype=torch.bfloat16,
                                        local_files_only=True, low_cpu_mem_usage=True)
    pipe.scheduler = scheduler_cls.from_config(pipe.scheduler.config, shift=shift)
    pipe.enable_sequential_cpu_offload(device='cuda:0')
    return pipe


def normalize_endpoint(z,config,family):
    if family=='hunyuan':return z*config.scaling_factor
    if family!='wan22':raise ValueError('Unknown VAE family')
    if z.ndim!=5 or z.shape[1]!=16:raise ValueError('Expected Wan A14B16-channel latent')
    mean=torch.as_tensor(config.latents_mean,device=z.device,dtype=torch.float32).view(1,16,1,1,1)
    std=torch.as_tensor(config.latents_std,device=z.device,dtype=torch.float32).view(1,16,1,1,1)
    if not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std<=0).any():
        raise ValueError('Invalid Wan latent normalization')
    return (z.float()-mean)/std


class SGOVAE:
    """Mode-only façade used by native SGO, never installed into the pipeline."""
    def __init__(self,vae):
        self._vae=vae
        self.config=SimpleNamespace(scaling_factor=1.0)

    @property
    def dtype(self):return self._vae.dtype

    def encode(self,pixels):
        distribution=self._vae.encode(pixels).latent_dist
        class NormalizedMode:
            def mode(inner):return normalize_endpoint(distribution.mode(),self._vae.config,'wan22')
        return SimpleNamespace(latent_dist=NormalizedMode())


def native_call_kwargs(kwargs,family,mode):
    """Translate upstream SGO's Hunyuan-specific call to the selected model."""
    if family not in ('hunyuan','wan22') or mode not in ('i2v','t2v'):
        raise ValueError('Unknown model family/mode')
    result=dict(kwargs)
    if mode=='t2v':result.pop('image',None)
    if family=='wan22':
        # Native Hunyuan SGO and final inversion use a one-image list. Wan's
        # actual I2V input validator accepts a tensor or PIL image, not a list.
        if mode=='i2v' and isinstance(result.get('image'),(list,tuple)):
            if len(result['image'])!=1:raise ValueError('Wan native extraction requires one conditioning image')
            result['image']=result['image'][0]
        result['guidance_scale']=5
        # Both Wan A14B experts use the same declared guidance value.
        result['guidance_scale_2']=5
    return result
