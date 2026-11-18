import numpy as np
import pytest
import torch
from last.coding import BCH512
from last.controlled_reader import decode,decode_oracle
from last.energy_calibration import DEFINITION


def test_selectors_share_fusion_and_recover_known_message():
    truth=np.arange(512,dtype=np.uint8)%2
    signs=torch.tensor(BCH512().encode(truth),dtype=torch.float32)*2-1
    generator=torch.Generator().manual_seed(711)
    corr=torch.randn(2,16,592,generator=generator)*.01
    corr[0,0]=signs;corr[1,1]=signs*20
    nodes=[dict(start=1,end=4,segment=0),dict(start=5,end=8,segment=0)]
    calibration=dict(schema_version=1,definition=DEFINITION,wrong_keys_per_candidate=64,groups=16,center=[0.]*16,scale=[1.]*16)
    outputs=[decode(corr,nodes,reader,calibration) for reader in ('received','ccta','calibrated_energy')]
    outputs.append(decode_oracle(torch.stack([corr[0,0],corr[1,1]]),[0,1]))
    for bits,soft,meta in outputs:
        assert np.array_equal(bits,truth)
        assert torch.allclose(soft,outputs[0][1])
        assert meta['fusion']==outputs[0][2]['fusion']
    assert not outputs[-1][2]['blind']


def test_received_order_cannot_reuse_sliding_window_cache():
    nodes=[dict(start=0,end=3,segment=0)]
    with pytest.raises(ValueError,match='own fixed-prefix'):
        decode(torch.ones(1,16,592),nodes,'received')
    with pytest.raises(ValueError,match='calibration required'):
        decode(torch.ones(1,16,592),nodes,'calibrated_energy')
