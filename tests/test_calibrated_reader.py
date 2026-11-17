import copy
import torch
from last.calibrated_reader import align
from last.ccta import energy_fallback
from last.energy_calibration import DEFINITION


def test_development_bias_correction_recovers_spaced_chain():
    corr=torch.ones((2,16,592))
    corr[:,15]=10 # Strong nuisance position, removed by frozen development center.
    corr[0,0]=3;corr[1,1]=3
    nodes=[dict(start=1,end=4,segment=0),dict(start=5,end=8,segment=0)]
    calibration=dict(schema_version=1,definition=DEFINITION,wrong_keys_per_candidate=64,groups=16,
                     center=[1.]*15+[10.],scale=[1.]*16)
    frozen=copy.deepcopy(calibration)
    soft,meta=align(corr,nodes,calibration)
    assert [x['group'] for x in meta['selected']]==[0,1] and meta['groups']==2
    assert torch.allclose(soft,torch.ones(592)/torch.sqrt(torch.tensor(592.)))
    assert calibration==frozen
    # Default raw-energy behavior still chooses the high-energy nuisance slot.
    raw,old=energy_fallback(corr,nodes)
    assert old==dict(route='energy_spacing',groups=1) and torch.equal(raw,torch.full((592,),10.))


def test_spacing_rejects_shifted_neighbor_and_deduplicates_groups():
    corr=torch.ones((3,16,592));corr[0,0]=3;corr[1,1]=3;corr[2,0]=4
    nodes=[dict(start=1,end=4,segment=0),dict(start=6,end=9,segment=0),dict(start=15,end=18,segment=1)]
    calibration=dict(schema_version=1,definition=DEFINITION,wrong_keys_per_candidate=64,groups=16,center=[1.]*16,scale=[1.]*16)
    _,meta=align(corr,nodes,calibration)
    assert len(meta['selected'])==1 and meta['selected'][0]['candidate']==2
