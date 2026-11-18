"""Shared evidence readout for supplementary controlled comparisons.

Primary readers remain unchanged. Selection must return one vector per recovered
group; oracle selection is nonblind and must be labelled separately by callers.
"""
import torch
from .coding import BCH512

DEFINITION='one592-coefficient vector per unique group; L2 floor1e-8; equal group mean; BCH512'


def readout(evidence, groups):
    """No messages, truth labels, positions or attack maps enter fusion/decoding."""
    if (not isinstance(evidence,torch.Tensor) or evidence.ndim!=2
            or evidence.shape!=(len(groups),592) or not torch.isfinite(evidence).all()):
        raise ValueError('Expected finite selected-group x592 evidence')
    if (any(type(g) is not int or not 0<=g<16 for g in groups)
            or len(set(groups))!=len(groups)):
        raise ValueError('Each recovered group must occur exactly once')
    if len(groups):
        normalized=evidence.float()/evidence.float().norm(dim=1,keepdim=True).clamp_min(1e-8)
        soft=normalized.mean(dim=0)
    else:
        soft=torch.zeros(592,device=evidence.device)
    bits,decoder=BCH512().decode(soft.detach().cpu().numpy())
    return bits,soft,dict(fusion=DEFINITION,groups=list(groups),**decoder,
                          evidence_available=bool(groups),
                          scope='Controlled fusion only; no claim of alignment correctness or authentication')
