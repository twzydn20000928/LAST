"""Verify pinned native baseline noise interfaces, not generated-video robustness."""
import argparse,importlib,json,os,sys,time,traceback
from pathlib import Path
import numpy as np
import torch
from .upstream import verify

def load_class(method,upstream,manifest):
    verify(upstream,manifest)
    sys.path.insert(0,str(Path(upstream).resolve()))
    names={'videoshield':'VideoShieldWatermark','videomark':'VideoMarkWatermark','sigmark':'SIGMarkWatermark'}
    module=importlib.import_module('watermarks.'+method)
    if not Path(module.__file__).resolve().is_relative_to(Path(upstream).resolve()):raise ValueError('Imported another baseline installation')
    return getattr(module,names[method])

def main():
    p=argparse.ArgumentParser();p.add_argument('--method',choices=['videoshield','videomark','sigmark'],required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--manifest',type=Path,default=Path('configs/sigmark_source_manifest.json'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700);start=time.time();torch.set_num_threads(4)
    def failure(kind,value,tb):
        (a.output/'receipt.json').write_text(json.dumps(dict(status='failed',method=a.method,scope='CPU original-noise interface only',error=''.join(traceback.format_exception(kind,value,tb))),indent=2));sys.__excepthook__(kind,value,tb)
    sys.excepthook=failure
    manifest=json.loads(a.manifest.read_text());cls=load_class(a.method,a.upstream,manifest)
    settings=dict(video_h=512,video_w=512,video_f=65,latent_c=16,vae_scale_factor_spatial=8,vae_scale_factor_temporal=4,ch_factor=2,hw_factor=8,fr_factor=16,batch_size=1,seed=2025,dtype=torch.float32,device='cpu')
    watermark=cls(**settings)
    shape=watermark.get_watermark_message_shape()
    if int(np.prod(shape))!=512:raise ValueError(f'Unexpected information payload:{shape}')
    rng=np.random.default_rng(2025);truth=rng.integers(0,2,shape,dtype=np.uint8)
    torch.manual_seed(2025);np.random.seed(2025)
    initial=watermark.create_watermarked_latents(truth)
    if a.method=='videomark':
        # Freeze a nontrivial public diagnostic catalogue, never a singleton answer.
        candidates=rng.integers(0,2,(400,*shape[1:]),dtype=np.uint8);candidates[0]=truth[0]
        watermark.maintained_info['watermark_messages']=list(candidates)
        # Pinned upstream save/load disagree on plural/singular key names.
        # Preserve upstream code and add required aliases only to private state.
        watermark.maintained_info['encoding_key']=watermark.encoding_key
        watermark.maintained_info['decoding_key']=watermark.decoding_key
    state=a.output/'maintained_private.pkl'
    watermark.save_maintained_info(str(state))
    watermark=cls(**settings,maintained_info_path=str(state))
    recovered=np.asarray(watermark.extract_watermark(initial),dtype=np.uint8)
    if recovered.shape!=truth.shape:raise ValueError('Native output shape differs from payload')
    report=dict(status='completed',scope='CPU original-noise interface only; no video generation or attack',method=a.method,upstream_commit=manifest['commit'],information_bits=512,latent_shape=list(initial.shape),message_shape=shape,correct_bits=int((recovered==truth).sum()),seconds=time.time()-start,registration_candidates=400 if a.method=='videomark' else None)
    (a.output/'receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
