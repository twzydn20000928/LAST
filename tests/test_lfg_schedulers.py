import pytest
pytest.importorskip('diffusers')
import torch
from diffusers import FlowMatchEulerDiscreteScheduler,UniPCMultistepScheduler
from last.lfg_schedulers import LFGFlowEuler,LFGUniPC

@pytest.mark.parametrize('base_cls,guided_cls,config',[
    (FlowMatchEulerDiscreteScheduler,LFGFlowEuler,{'shift':7}),
    (UniPCMultistepScheduler,LFGUniPC,{'flow_shift':5,'use_flow_sigmas':True,'prediction_type':'flow_prediction'}),
])
@pytest.mark.parametrize('latent_frames',[16,17])
def test_guidance_timing_and_zero_strength_replay(monkeypatch,base_cls,guided_cls,config,latent_frames):
    import last.lfg_schedulers as module
    torch.manual_seed(1)
    baseline=base_cls(**config);guided=guided_cls(**config)
    baseline.set_timesteps(4);guided.set_timesteps(4)
    guided.alpha=0;guided.late_steps=2;guided.spread=torch.zeros(1,16,8,32,32)
    calls=[];original=module.perturbation
    def traced(*args,**kwargs):calls.append(int(guided.step_index));return original(*args,**kwargs)
    monkeypatch.setattr(module,'perturbation',traced)
    a=torch.randn(1,16,latent_frames,64,64);b=a.clone()
    for t in baseline.timesteps:
        prediction=torch.randn_like(a)
        a=baseline.step(prediction,t,a,return_dict=False)[0]
        b=guided.step(prediction,t,b,return_dict=False)[0]
        assert torch.allclose(a,b,atol=1e-6,rtol=1e-6)
    assert calls==[2,3]
