"""Orthonormal DCT-II selection and minimum signed-margin projection."""
import math
import torch

def dct_matrix(n, device, dtype=torch.float32):
    k = torch.arange(n, device=device, dtype=dtype)[:, None]
    x = torch.arange(n, device=device, dtype=dtype)[None, :]
    m = torch.cos(math.pi / n * (x + .5) * k) * math.sqrt(2 / n)
    m[0] /= math.sqrt(2)
    return m

def transform(z, inverse=False):
    h, w = z.shape[-2:]
    a, b = dct_matrix(h, z.device, z.dtype), dct_matrix(w, z.device, z.dtype)
    return a.T @ z @ b if inverse else a @ z @ b.T

def selected(spectrum):
    block = spectrum[..., 8:16, 8:22]
    if block.shape[-3:] != (16, 8, 14):
        raise ValueError("Expected [...,16 channels,>=16,>=22] spectrum")
    return block.flatten(-2)[..., 1:].flatten(-2)

def scatter(v, height=64, width=64):
    block = torch.zeros(*v.shape[:-1], 16, 112, device=v.device, dtype=v.dtype)
    block[..., 1:] = v.reshape(*v.shape[:-1], 16, 111)
    full = torch.zeros(*v.shape[:-1], 16, height, width, device=v.device, dtype=v.dtype)
    full[..., 8:16, 8:22] = block.reshape(*v.shape[:-1],16,8,14)
    return full

def margin_profile(mu=.5, groups=16, device="cpu"):
    p = torch.full((groups,), float(mu), device=device)
    p[0] = 0
    if groups >= 4: p[3] = 2 * mu
    return p

def embed(latents, codes, signs, mu=.5, fixed_target=False, uniform=False):
    if latents.shape != (1,16,17,64,64): raise ValueError("Expected normalized65-frame512-square latents")
    z = latents.float(); c = codes.to(device=z.device, dtype=torch.float32)
    if c.shape != (16,592,1776): raise ValueError("Wrong protocol codebook")
    b = torch.as_tensor(signs, device=z.device, dtype=torch.float32)
    if b.shape != (592,) or not bool(torch.all((b==1)|(b==-1))): raise ValueError("Expected592 signs")
    groups = z[0,:,1:].permute(1,0,2,3)
    f = selected(transform(groups)); r = torch.einsum('gmd,gd->gm',c,f)
    p = torch.full((16,),mu,device=z.device) if uniform else margin_profile(mu,device=z.device)
    delta = p[:,None]*b-r if fixed_target else b*torch.relu(p[:,None]-r*b)
    update = torch.einsum('gmd,gm->gd',c,delta)
    result = z.clone();result[0,:,1:] += transform(scatter(update),inverse=True).permute(1,0,2,3)
    return result

def feature(normalized_five_frame_latents):
    f = selected(transform(normalized_five_frame_latents[0,:,1].float()))
    return f / (f.square().mean().sqrt() + 1e-8)
