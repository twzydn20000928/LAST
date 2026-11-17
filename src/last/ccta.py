"""Truth-free candidate-chain scoring and documented energy-spacing fallback."""
import torch

def energy_fallback(corr, nodes):
    energy, ids = corr.abs().mean(-1).max(-1); slots={}
    for segment in sorted({n['segment'] for n in nodes}):
        choices=sorted([i for i,n in enumerate(nodes) if n['segment']==segment],key=lambda i:(nodes[i]['end'],nodes[i]['start']))
        dp={};previous={}
        for a in choices:
            dp[a]=float(energy[a]);previous[a]=None
            for q in choices:
                if q==a:break
                gap=int(ids[a]-ids[q])
                if gap>0 and nodes[q]['end']<nodes[a]['start'] and nodes[a]['start']-nodes[q]['start']==4*gap:
                    score=dp[q]+float(energy[a])
                    if score>dp[a]:dp[a]=score;previous[a]=q
        if not choices:continue
        a=max(choices,key=lambda i:(dp[i],-nodes[i]['start']))
        while a is not None:
            g=int(ids[a])
            if g not in slots or energy[a]>energy[slots[g]]:slots[g]=a
            a=previous[a]
    if not slots:
        a,g=divmod(int(corr.abs().mean(-1).argmax()),corr.shape[1]);slots[g]=a
    return sum(corr[a,g] for g,a in slots.items()), {'route':'energy_spacing','groups':len(slots)}

def align(features, nodes, codes, reader='ccta'):
    if len(nodes)==0:return torch.zeros(codes.shape[1]),{'route':'no_evidence','groups':0}
    corr=torch.einsum('nd,gmd->ngm',features.float(),codes.to(features.device).float())
    if reader=='energy':return energy_fallback(corr,nodes)
    if reader!='ccta':raise ValueError(reader)
    selected=[]
    for segment in sorted({n['segment'] for n in nodes}):
        lookup={n['start']:i for i,n in enumerate(nodes) if n['segment']==segment and n['end']-n['start']==3}
        best=None
        for start in sorted(lookup):
            for first in range(codes.shape[0]):
                rows=[]
                for g in range(first,codes.shape[0]):
                    i=lookup.get(start+4*(g-first))
                    if i is None:break
                    v=corr[i,g];rows.append(v/v.norm().clamp_min(1e-8))
                if len(rows)<2:continue
                stack=torch.stack(rows);q=len(rows);score=float((stack.sum(0).square().sum()-q)/(q-1))
                rank=(score,q,-start,-first)
                if best is None or rank>best[0]:best=(rank,stack.mean(0))
        if best is not None:selected.append(best)
    if not selected:return energy_fallback(corr,nodes)
    weights=[max(x[0][0],1e-8) for x in selected]
    return sum(w*x[1] for w,x in zip(weights,selected))/sum(weights),{'route':'ccta','groups':sum(x[0][1] for x in selected),'chains':[{'score':x[0][0],'length':x[0][1],'start':-x[0][2],'first_group':-x[0][3]} for x in selected]}
