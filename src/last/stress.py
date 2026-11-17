"""Supplement temporal edits; export and reread before a separate blind reader."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from .temporal import attack_map
from .video import load_mp4,export_mp4

def midpoint(a,b):
    import cv2
    from PIL import Image
    a=np.asarray(a);b=np.asarray(b)
    if a.shape!=b.shape:raise ValueError('Mismatched interpolation frames')
    gray_a=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);gray_b=cv2.cvtColor(b,cv2.COLOR_RGB2GRAY)
    f=cv2.calcOpticalFlowFarneback(gray_a,gray_b,None,.5,3,15,3,5,1.2,0)
    r=cv2.calcOpticalFlowFarneback(gray_b,gray_a,None,.5,3,15,3,5,1.2,0)
    y,x=np.mgrid[:a.shape[0],:a.shape[1]].astype(np.float32)
    warp=lambda image,flow:cv2.remap(image.astype(np.float32),x-.5*flow[...,0],y-.5*flow[...,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    return Image.fromarray(np.rint(np.clip((warp(a,f)+warp(b,r))/2,0,255)).astype(np.uint8))

def edit(frames,attack,video_id,seed=0,donor=None):
    if len(frames)!=65:raise ValueError('Supplement protocol starts from65frames')
    digest=hashlib.sha256(f'LAST-stress-v1:{video_id}:{attack}:{seed}'.encode()).digest()
    rng=np.random.Generator(np.random.PCG64(int.from_bytes(digest,'big')))
    if attack in ('drop10','drop30','drop45','drop30_crf28'):
        count=int(attack.split('_')[0][4:]);mapping=attack_map(video_id,'drop',seed,65,count)
        return [frames[i] for i in mapping],dict(source_indices=mapping)
    if attack=='duplicate30':
        chosen=set(rng.choice(65,30,replace=False).tolist());mapping=[]
        for i in range(65):mapping.extend([i,i] if i in chosen else [i])
        return [frames[i] for i in mapping],dict(source_indices=mapping,duplicated_indices=sorted(chosen))
    if attack=='natural30':
        if donor is None or len(donor)<30:raise ValueError('Natural insertion requires an unwatermarked donor of at least30frames')
        if any(f.size!=frames[0].size for f in donor):raise ValueError('Donor must match spatial size')
        start=int(rng.integers(len(donor)-29));boundary=int(rng.integers(66))
        return frames[:boundary]+donor[start:start+30]+frames[boundary:],dict(boundary=boundary,donor_start=start,donor_count=30)
    if attack=='interpolate30':
        pairs=set(rng.choice(64,30,replace=False).tolist());output=[]
        for i,f in enumerate(frames):
            output.append(f)
            if i in pairs:output.append(midpoint(f,frames[i+1]))
        return output,dict(midpoint_pairs=sorted(pairs))
    raise ValueError(attack)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',type=Path,required=True);p.add_argument('--video-id',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--attack',choices=['drop10','drop30','drop45','duplicate30','natural30','interpolate30','drop30_crf28'],required=True)
    p.add_argument('--seed',type=int,choices=range(5),default=0);p.add_argument('--donor-reference',type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    frames=load_mp4(a.video);donor=load_mp4(a.donor_reference) if a.donor_reference else None
    output,mapping=edit(frames,a.attack,a.video_id,a.seed,donor)
    destination=a.output/'received.mp4';command=export_mp4(output,destination,crf=28 if a.attack=='drop30_crf28' else 18)
    reread=load_mp4(destination)
    if len(reread)!=len(output):raise ValueError('Codec changed frame count')
    result=dict(status='completed_attack_export',video_id=a.video_id,attack=a.attack,seed=a.seed,source_sha256=hashlib.sha256(a.video.read_bytes()).hexdigest(),received_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),frames=len(reread),mapping=mapping,codec_command=command,scope='Attack construction only; no extraction or accuracy claim')
    if a.donor_reference:result['donor_sha256']=hashlib.sha256(a.donor_reference.read_bytes()).hexdigest()
    (a.output/'attack.json').write_text(json.dumps(result,indent=2));print(json.dumps({'status':result['status'],'frames':len(reread)}))

if __name__=='__main__':main()
