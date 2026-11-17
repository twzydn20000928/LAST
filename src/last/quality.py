"""Explicit paired RGB fidelity metrics; not a replacement for official VBench."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from .video import load_mp4

def fidelity(reference,marked):
    if len(reference)!=len(marked) or not reference:raise ValueError('Pair must have the same nonzero frame count')
    errors=[];ssims=[]
    for left,right in zip(reference,marked):
        a=np.asarray(left,dtype=np.float64)/255;b=np.asarray(right,dtype=np.float64)/255
        if a.shape!=b.shape or a.ndim!=3 or a.shape[-1]!=3 or min(a.shape[:2])<11:raise ValueError('Expected matched RGB frames at least11square')
        errors.append(float(np.mean((a-b)**2)))
        filt=lambda x:gaussian_filter(x,sigma=(1.5,1.5,0),truncate=10/6,mode='reflect')
        ma,mb=filt(a),filt(b);va=filt(a*a)-ma*ma;vb=filt(b*b)-mb*mb;cov=filt(a*b)-ma*mb
        score=((2*ma*mb+.01**2)*(2*cov+.03**2))/((ma*ma+mb*mb+.01**2)*(va+vb+.03**2))
        ssims.append(float(score[5:-5,5:-5].mean()))
    mse=float(np.mean(errors))
    return dict(frames=len(errors),rgb_mse=mse,psnr_db=-10*math.log10(mse) if mse else None,identical=mse==0,ssim=float(np.mean(ssims)),definition='PSNR from global RGB MSE in[0,1]; SSIM11x11 Gaussian sigma1.5 population covariance valid centers, mean RGB and frames; identical PSNR is +infinity represented by null+identical=true')

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--marked',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=fidelity(load_mp4(a.reference),load_mp4(a.marked))
    result.update(reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),marked_sha256=hashlib.sha256(a.marked.read_bytes()).hexdigest(),scope='paired fidelity, not V-score or temporal perceptual quality')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
