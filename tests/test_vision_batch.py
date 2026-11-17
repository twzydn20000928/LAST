import torch
import pytest
from last.vision_batch import forward_images


def test_independent_frames_keep_order_count_and_values():
    x=torch.arange(17*3*4*4).reshape(17,3,4,4).float();sizes=[]
    def forward(v):sizes.append(len(v));return v.mean((-1,-2))
    y=forward_images(forward,x,4)
    assert sizes==[4,4,4,4,1] and torch.equal(y,x.mean((-1,-2)))
    with pytest.raises(ValueError):forward_images(lambda v:v[:1],x,4)
