"""Supplement selectors with one shared fusion/decoder; primary readers unchanged."""
import torch
from .controlled_fusion import readout
from .calibrated_reader import align as calibrated_align
from .ccta import energy_fallback


def _ccta_selection(corr,nodes,duration):
    slots={};chains=[]
    for segment in sorted({n['segment'] for n in nodes}):
        lookup={n['start']:i for i,n in enumerate(nodes) if n['segment']==segment and n['end']-n['start']==duration-1}
        best=None
        for start in sorted(lookup):
            for first in range(16):
                selected=[];rows=[]
                for group in range(first,16):
                    index=lookup.get(start+duration*(group-first))
                    if index is None:break
                    vector=corr[index,group]
                    rows.append(vector/vector.norm().clamp_min(1e-8));selected.append((index,group))
                if len(rows)<2:continue
                stack=torch.stack(rows);count=len(rows)
                score=float((stack.sum(0).square().sum()-count)/(count-1))
                rank=(score,count,-start,-first)
                if best is None or rank>best[0]:best=(rank,selected)
        if best is None:continue
        rank,selected=best;chains.append(dict(segment=segment,score=rank[0],length=rank[1],start=-rank[2],first_group=-rank[3]))
        for index,group in selected:
            # Shared readout has one observation per group. Unlike primary CCTA,
            # repeated slots across segments use the highest-ranked chain.
            if group not in slots or rank>slots[group][0]:slots[group]=(rank,index)
    return [dict(candidate=index,group=group) for group,(_,index) in sorted(slots.items())],chains


def decode(correlations,nodes,reader,calibration=None,group_frames=4):
    if (correlations.ndim!=3 or correlations.shape!=(len(nodes),16,592)
            or not torch.isfinite(correlations).all() or group_frames<1):
        raise ValueError('Expected finite candidate x16x592 correlations')
    if reader not in ('received','ccta','calibrated_energy'):raise ValueError('Unknown controlled reader')
    for node in nodes:
        if any(type(node[k]) is not int for k in ('start','end','segment')) or node['start']<0 or not 0<=node['end']-node['start']<group_frames:
            raise ValueError('Invalid candidate interval')
    if len({(n['segment'],n['start']) for n in nodes})!=len(nodes):raise ValueError('Duplicate candidate start')
    meta=dict(reader=reader,controlled=True,blind=True)
    if not nodes:
        selected=[]
    elif reader=='received':
        if len(nodes)>16 or any(n['start']!=1+group_frames*i or n['segment']!=0 for i,n in enumerate(nodes)):
            raise ValueError('Received-order requires its own fixed-prefix candidate cache')
        selected=[dict(candidate=i,group=i) for i in range(len(nodes))]
    elif reader=='calibrated_energy':
        if calibration is None:raise ValueError('Frozen development calibration required')
        _,selection=calibrated_align(correlations,nodes,calibration,group_frames)
        selected=selection['selected'];meta['selection']=selection
    else:
        selected,chains=_ccta_selection(correlations,nodes,group_frames);meta['chains']=chains
        if not selected:
            _,fallback=energy_fallback(correlations,nodes,group_frames,normalized_fusion=True)
            selected=fallback['selected'];meta['fallback']='raw_energy_spacing_selection'
        meta['duplicate_policy']='Highest-ranked chain per group; earlier segment on exact tie'
    groups=[int(x['group']) for x in selected]
    evidence=torch.stack([correlations[x['candidate'],x['group']] for x in selected]) if selected else correlations.new_empty((0,592))
    bits,soft,fusion=readout(evidence,groups)
    meta.update(fusion,selected=selected)
    return bits,soft,meta


def decode_oracle(selected_evidence,original_groups):
    """Caller supplies evidence from true-map reconstruction, never blind search."""
    bits,soft,meta=readout(selected_evidence,original_groups)
    meta.update(reader='oracle',controlled=True,blind=False,
                scope='True-map-assisted evidence selection; shared fusion only, not deployable extraction')
    return bits,soft,meta
