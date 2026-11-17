"""Explicit independent-image microbatching; does not subsample frames."""
import torch


def forward_images(forward,images,batch_size):
    if batch_size<1:raise ValueError('Positive visual batch size required')
    if not isinstance(images,torch.Tensor) or images.ndim!=4:
        raise ValueError('Expected [frames,channels,height,width] image tensor')
    if len(images)==0:raise ValueError('No image frames')
    pieces=[forward(images[i:i+batch_size]) for i in range(0,len(images),batch_size)]
    if any(not isinstance(p,torch.Tensor) or p.shape[0]!=min(batch_size,len(images)-i*batch_size) for i,p in enumerate(pieces)):
        raise ValueError('Vision tower changed frame count')
    return torch.cat(pieces,dim=0)
