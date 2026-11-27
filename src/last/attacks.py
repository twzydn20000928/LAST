"""Pixel and frame edits shared by the CPU CLI and watermark evaluation."""
import hashlib

import numpy as np

from .temporal import attack_map


def attacked(frames, name, video_id, seed=0):
    from PIL import Image
    import cv2
    digest=hashlib.sha256(f'LAST-pixels-v1:{video_id}:{name}:{seed}'.encode()).digest()
    rng=np.random.Generator(np.random.PCG64(int.from_bytes(digest,'big')))
    if name in ('clean','compression'):return frames, None
    if name in ('drop','clip','insert'):
        mapping=attack_map(video_id,name,seed,frames=len(frames))
        shape=np.asarray(frames[0]).shape
        # The paper does not specify the noise-frame distribution; fix uniform RGB8.
        return [frames[i] if i>=0 else Image.fromarray(rng.integers(0,256,shape,dtype=np.uint8)) for i in mapping], mapping
    output=[]
    for f in frames:
        x=np.asarray(f)
        if name=='noise':x=np.rint(np.clip(x/255.+rng.normal(0,.05,x.shape),0,1)*255).astype(np.uint8)
        elif name=='blur':x=cv2.GaussianBlur(x,(5,5),1)
        else:raise ValueError(name)
        output.append(Image.fromarray(x))
    return output,None
