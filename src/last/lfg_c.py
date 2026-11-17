"""Explicit shared-DCT-codebook LFG control, not the primary/native LFG writer."""
import math
import torch
from .elmc import transform, selected, scatter


def watermark(codes, signs):
    c=torch.as_tensor(codes,dtype=torch.float32)
    b=torch.as_tensor(signs,dtype=torch.float32,device=c.device)
    if c.shape!=(16,592,1776) or b.shape!=(592,):raise ValueError('Expected shared LAST carrier geometry')
    if not bool(torch.all((b==1)|(b==-1))):raise ValueError('Expected signed coded bits')
    # Orthonormal rows give ||C^T b||^2=592; scale to mean coordinate energy 1.
    return torch.einsum('gmd,m->gd',c,b)*math.sqrt(1776/592)


def perturbation(clean, spread, alpha=.15):
    if clean.shape not in ((1,16,17,64,64),(1,16,16,64,64)):raise ValueError('Expected full17 or dynamic16 latent frames')
    if spread.shape!=(16,1776):raise ValueError('Expected shared DCT watermark')
    if alpha<0 or not math.isfinite(alpha):raise ValueError('Expected finite nonnegative strength')
    dynamic=clean[:,:,1:] if clean.shape[2]==17 else clean
    groups=dynamic[0].float().permute(1,0,2,3)
    coefficients=selected(transform(groups))
    scale=coefficients.std(-1,keepdim=True,unbiased=False)
    delta=alpha*scale*spread.to(device=clean.device,dtype=torch.float32)
    update=transform(scatter(delta),inverse=True).permute(1,0,2,3)[None]
    return torch.cat([torch.zeros_like(clean[:,:,:1]),update],dim=2) if clean.shape[2]==17 else update
