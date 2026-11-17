"""LFG paper-equation adaptation for the frozen65frame/592coded-bit comparison.

Not official author code. Key stream and temporal carrier packing are explicit
adaptation choices; see docs/BASELINES.md. No LAST orthogonal carriers are used.
"""
import hashlib,math
import numpy as np
import torch
import torch.nn.functional as F

def lowpass(z):
    if z.ndim!=5 or any(n%2 for n in z.shape[-3:]):raise ValueError('Haar LLL needs even T,H,W')
    return F.avg_pool3d(z.float(),2,2)*math.sqrt(8)

def lift(w):
    return w.repeat_interleave(2,2).repeat_interleave(2,3).repeat_interleave(2,4)/math.sqrt(8)

def carriers(key, pair):
    if len(key)!=32 or not 0<=pair<8:raise ValueError('Expected32byte key and Haar pair0..7')
    seed=int.from_bytes(hashlib.sha256(b'LAST-LFG-v1\0'+key+pair.to_bytes(4,'big')).digest(),'big')
    rng=np.random.Generator(np.random.PCG64(seed))
    return torch.from_numpy(rng.integers(0,2,(1184,16384),dtype=np.int8)*2-1)

def watermark(key, signs):
    signs=torch.as_tensor(signs,dtype=torch.float32)
    if signs.shape!=(592,) or not bool(torch.all((signs==1)|(signs==-1))):raise ValueError('Expected592signs')
    repeated=signs.repeat(2)
    return torch.stack([(repeated@carriers(key,p).float()/math.sqrt(1184)).reshape(16,32,32) for p in range(8)],dim=1)[None]

def perturbation(clean, spread, alpha=.15):
    # Hunyuan I2V token_replace keeps the conditioning frame outside scheduler.step.
    # T2V/Wan pass all17 frames; both paths guide the same16 dynamic frames.
    if clean.shape not in ((1,16,17,64,64),(1,16,16,64,64)):
        raise ValueError(f'Expected full17 or dynamic16 latent frames, got {tuple(clean.shape)}')
    if spread.shape!=(1,16,8,32,32):raise ValueError('Incorrect Haar carrier geometry')
    if alpha<0 or not math.isfinite(alpha):raise ValueError('Expected finite nonnegative strength')
    dynamic=clean[:,:,1:] if clean.shape[2]==17 else clean
    band=lowpass(dynamic)
    sigma=band.std((2,3,4),keepdim=True,unbiased=False)
    delta=lift(alpha*sigma*spread.to(device=clean.device,dtype=torch.float32))
    return torch.cat([torch.zeros_like(clean[:,:,:1]),delta],dim=2) if clean.shape[2]==17 else delta

def scores(encoded,key):
    if encoded.shape!=(1,16,17,64,64):raise ValueError('Reader requires aligned65frame latent')
    band=lowpass(encoded[:,:,1:]);groups=[]
    for p in range(8):
        code=carriers(key,p).to(device=band.device,dtype=torch.float32)
        groups.append((code@band[0,:,p].flatten()/16384).reshape(2,592))
    return torch.cat(groups).mean(0).cpu()

def align_received_frames(frames):
    if not frames:raise ValueError('No received frames')
    return list(frames[:65])+[frames[-1]]*max(0,65-len(frames))
