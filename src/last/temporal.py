"""Versioned deterministic attack maps and CPU Farneback segmentation."""
import hashlib
import numpy as np

def attack_map(video_id, attack, seed=0, frames=65, count=30):
    raw=f'LAST-v1\0{video_id}\0{attack}\0{seed}'.encode()
    rng=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(raw).digest(),'big')))
    if attack=='drop':
        removed=set(rng.choice(frames,count,replace=False).tolist());return [i for i in range(frames) if i not in removed]
    if attack=='clip':
        start=int(rng.integers(frames-count+1));return list(range(start))+list(range(start+count,frames))
    if attack=='insert':
        slots=set(rng.choice(frames+count,count,replace=False).tolist());it=iter(range(frames));return [-1 if i in slots else next(it) for i in range(frames+count)]
    raise ValueError(attack)

def segments(frames):
    import cv2
    if not frames:return []
    gray=[cv2.cvtColor(cv2.resize(np.asarray(f),(128,128)),cv2.COLOR_RGB2GRAY) for f in frames]
    energy=[]
    for a,b in zip(gray[:-1],gray[1:]):
        flow=cv2.calcOpticalFlowFarneback(a,b,None,.5,3,15,3,5,1.2,0)
        energy.append(float(np.median(np.linalg.norm(flow,axis=-1)))/np.hypot(128,128))
    med=np.median(energy) if energy else 0;mad=np.median(np.abs(np.asarray(energy)-med)) if energy else 0
    cuts=[0]+[i+1 for i,e in enumerate(energy) if e>.01 and e>med+4*mad]+[len(frames)]
    return [(a,b-1) for a,b in zip(cuts[:-1],cuts[1:])]

def windows(segment_list, scan=True, group_frames=4):
    if group_frames<1:raise ValueError('Positive window length required')
    for segment,(lo,hi) in enumerate(segment_list):
        if hi-lo+1<group_frames:
            yield {'start':lo,'end':hi,'segment':segment,'indices':list(range(lo,hi+1))+[hi]*(group_frames-(hi-lo+1)),'padded':True}
        else:
            for start in range(lo,hi-group_frames+2,1 if scan else group_frames):
                yield {'start':start,'end':start+group_frames-1,'segment':segment,'indices':list(range(start,start+group_frames)),'padded':False}
