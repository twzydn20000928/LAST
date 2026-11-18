import numpy as np
import pytest
import torch
from last.coding import BCH512
from last.controlled_fusion import readout


def test_common_readout_is_invariant_to_group_amplitudes_and_order():
    truth=np.arange(512,dtype=np.uint8)%2
    signs=torch.as_tensor(BCH512().encode(truth),dtype=torch.float32)*2-1
    rows=torch.stack([signs,signs*40,signs*.02])
    bits,soft,meta=readout(rows,[2,4,7])
    other,permuted,_=readout(rows[[2,0,1]],[7,2,4])
    assert np.array_equal(bits,truth) and np.array_equal(other,truth)
    assert torch.allclose(soft,permuted) and meta['evidence_available']


def test_duplicate_groups_and_missing_evidence_are_explicit():
    with pytest.raises(ValueError,match='exactly once'):readout(torch.ones(2,592),[0,0])
    _,soft,meta=readout(torch.empty(0,592),[])
    assert not meta['evidence_available'] and torch.equal(soft,torch.zeros(592))
