import numpy as np
import torch
from last.coding import BCH512
from last.carriers import group_code
from last.elmc import transform,selected,scatter
from last.ccta import align
from last.temporal import attack_map

def test_bch_corrects_eight_errors_and_checks_parity():
    codec=BCH512();rng=np.random.default_rng(17);bits=rng.integers(0,2,512,dtype=np.uint8)
    packet=codec.encode(bits);packet[[0,19,55,103,511,512,555,591]]^=1
    got,info=codec.decode(packet.astype(float)*2-1)
    assert info['bch_success'] and np.array_equal(got,bits)

def test_codebook_deterministic_orthogonal_separated():
    a=group_code(bytes(32),0,64,12);b=group_code(bytes(32),0,64,12)
    assert np.array_equal(a,b)
    assert np.allclose(a@a.T,np.eye(12),atol=1e-6)
    assert not np.allclose(a,group_code(bytes(32),1,64,12))

def test_dct_and_mask_roundtrip():
    torch.manual_seed(1);x=torch.randn(2,16,64,64)
    assert torch.allclose(transform(transform(x),True),x,atol=5e-5)
    f=selected(transform(x));assert f.shape==(2,1776)
    assert torch.equal(selected(scatter(f)),f)
    assert torch.count_nonzero(scatter(f)[...,8,8])==0

def test_ccta_recovers_message_without_truth_or_attack_map():
    c=torch.stack([torch.from_numpy(group_code(bytes(32),g,64,12)) for g in range(4)])
    signs=torch.tensor([1.,-1.]*6)
    features=torch.stack([c[g].T@signs for g in range(4)])
    nodes=[{'segment':0,'start':i*4,'end':i*4+3} for i in range(4)]
    soft,meta=align(features,nodes,c)
    assert torch.equal(soft>0,signs>0) and meta['route']=='ccta' and meta['groups']==4

def test_attack_maps_shared_and_deterministic():
    for attack,length in [('drop',35),('clip',35),('insert',95)]:
        a=attack_map('clip000',attack);assert a==attack_map('clip000',attack) and len(a)==length
    assert attack_map('clip000','drop')!=attack_map('clip000','drop',seed=1)

def test_minimum_margin_constraints_and_excluded_coordinates():
    from last.elmc import embed,margin_profile
    torch.manual_seed(3);z=torch.randn(1,16,17,64,64)
    c=torch.eye(1776)[:592].repeat(16,1,1);b=torch.tensor([1.,-1.]*296)
    y=embed(z,c,b)
    f=selected(transform(y[0,:,1:].permute(1,0,2,3)))
    response=torch.einsum('gmd,gd->gm',c,f)
    assert torch.all(response*b>=margin_profile()[:,None]-1e-4)
    assert torch.equal(y[:,:,0],z[:,:,0])
    change=transform((y-z)[0,:,1:].permute(1,0,2,3))
    assert change[...,8,8].abs().max()<1e-4
    fixed=embed(z,c,b,fixed_target=True)
    assert (y-z).square().sum() <= (fixed-z).square().sum()+1e-3
