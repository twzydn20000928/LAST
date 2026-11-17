import torch
from last.ccta import align_correlations
from last.temporal import windows


def test_haar_pair_chains_use_eight_frame_spacing_and_exclude_partial_windows():
    nodes=list(windows([(0,15)],scan=False,group_frames=8))
    assert [n['indices'] for n in nodes]==[list(range(8)),list(range(8,16))]
    corr=torch.zeros(2,8,4)
    corr[0,2]=torch.tensor([1.,-1.,1.,-1.]);corr[1,3]=corr[0,2]
    soft,meta=align_correlations(corr,nodes,group_frames=8)
    assert meta['route']=='ccta' and meta['chains'][0]['first_group']==2
    assert torch.equal(soft.sign(),corr[0,2].sign())
    padded=list(windows([(0,2)],group_frames=8))
    assert padded[0]['indices']==[0,1,2,2,2,2,2,2] and padded[0]['padded']
