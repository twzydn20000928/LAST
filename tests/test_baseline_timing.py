import pytest
from last.baseline_timing import recover_frames,NativePipeline


def test_shared_inversion_loader_selects_pipeline_and_scheduler():
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock, patch
    import torch
    from last.native_model_adapter import load_inversion_pipeline

    for family, vae_name, i2v, t2v, shift in (
        ('hunyuan','AutoencoderKLHunyuanVideo','HunyuanVideoImageToVideoPipeline','HunyuanVideoPipeline',7),
        ('wan22','AutoencoderKLWan','WanImageToVideoPipeline','WanPipeline',5),
    ):
        for mode, selected in [('i2v',i2v), ('t2v',t2v)]:
            names = ('AutoencoderKLHunyuanVideo','AutoencoderKLWan','HunyuanVideoImageToVideoPipeline',
                     'HunyuanVideoPipeline','WanImageToVideoPipeline','WanPipeline')
            classes = {name: Mock() for name in names}
            scheduler = Mock()
            pipe = classes[selected].from_pretrained.return_value
            config = pipe.scheduler.config
            with patch.dict(sys.modules, diffusers=SimpleNamespace(**classes)):
                assert load_inversion_pipeline('checkpoint',family,mode,scheduler) is pipe
            vae = classes[vae_name].from_pretrained.return_value
            classes[vae_name].from_pretrained.assert_called_once_with(
                'checkpoint', subfolder='vae', torch_dtype=torch.float32, local_files_only=True)
            classes[selected].from_pretrained.assert_called_once_with(
                'checkpoint', vae=vae, torch_dtype=torch.bfloat16, local_files_only=True, low_cpu_mem_usage=True)
            vae.enable_tiling.assert_called_once_with()
            scheduler.from_config.assert_called_once_with(config, shift=shift)
            assert pipe.scheduler is scheduler.from_config.return_value
            pipe.enable_sequential_cpu_offload.assert_called_once_with(device='cuda:0')


def test_temporal_timing_calls_native_sgo_instead_of_length_only_alignment():
    calls=[]
    class WM:
        def segment_group_ordering(self,*args):
            calls.append(args);return list(range(65))
    frames=list(range(35));pipe=object()
    def forbidden(*args):raise AssertionError('SIGMark must execute SGO')
    assert len(recover_frames(frames,'sigmark',True,WM(),pipe,forbidden))==65
    assert calls==[(frames,65,True,True,pipe)]
    with pytest.raises(ValueError):recover_frames(frames,'sigmark',False,WM(),pipe,forbidden)


def test_native_timing_adapter_preserves_inversion_options():
    calls=[]
    class Latent:
        def to(self,**kwargs):assert kwargs=={'dtype':'bf16'};return 'cast'
    def pipeline(**kwargs):calls.append(kwargs);return 'result'
    adapter=NativePipeline(pipeline,'t2v','bf16')
    assert adapter(image='unused',latents=Latent(),num_inference_steps=50)=='result'
    assert calls==[dict(latents='cast',num_inference_steps=50)]
    assert adapter.calls==1
