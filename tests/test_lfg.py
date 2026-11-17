import torch
from last.lfg import lowpass,lift,perturbation,align_received_frames

def test_haar_projection_and_first_causal_frame():
    torch.manual_seed(7)
    band=torch.randn(1,16,8,32,32)
    assert torch.allclose(lowpass(lift(band)),band,atol=1e-6)
    z=torch.randn(1,16,17,64,64)
    d=perturbation(z,band)
    assert torch.count_nonzero(d[:,:,:1])==0
    assert torch.count_nonzero(perturbation(z,band,0))==0
    constant=torch.ones_like(z)
    assert torch.count_nonzero(perturbation(constant,band))==0

def test_unaligned_reader_does_not_invent_positions():
    assert align_received_frames(list(range(35)))==list(range(35))+[34]*30
    assert align_received_frames(list(range(95)))==list(range(65))
