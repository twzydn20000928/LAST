import pytest
from last.baseline_timing import recover_frames,NativePipeline


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
