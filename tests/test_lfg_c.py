import math
import torch
from last.lfg_c import watermark,perturbation
from last.elmc import selected,transform


def test_shared_additive_guidance_preserves_carrier_directions_and_causal_frame():
    codes=torch.eye(1776)[:592].unsqueeze(0).expand(16,-1,-1)
    signs=torch.ones(592);signs[::2]=-1
    spread=watermark(codes,signs)
    assert torch.allclose(spread.square().mean(-1),torch.ones(16))
    z=torch.randn(1,16,17,64,64)
    delta=perturbation(z,spread,.05)
    assert torch.count_nonzero(delta[:,:,:1])==0
    assert torch.equal(delta[:,:,1:],perturbation(z[:,:,1:],spread,.05))
    recovered=selected(transform(delta[0,:,1:].permute(1,0,2,3)))
    assert torch.all(torch.einsum('gmd,gd->gm',codes,recovered)*signs>0)
    sigma=selected(transform(z[0,:,1:].permute(1,0,2,3))).std(-1,unbiased=False)
    assert torch.allclose(recovered.norm(dim=-1),.05*sigma*math.sqrt(1776),atol=1e-5,rtol=1e-5)
    assert torch.count_nonzero(perturbation(z,spread,0))==0
