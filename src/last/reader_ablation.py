"""Evaluate paper reader ablations on identical, already exported attack videos."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .coding import BCH512
from .evaluate import extract
from .report import CONDITIONS
from .video import load_mp4

VARIANTS={'full':('ccta',True),'without_cgc':('energy',True),'without_sws':('ccta',False),'without_ccta':('received',False)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['run','model-dir','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(.20)
    from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
    from diffusers.video_processor import VideoProcessor
    generation=json.loads((a.run/'receipt.json').read_text())
    if generation.get('status')!='completed' or generation.get('method')!='last' or generation['family']!=a.family:raise ValueError('Require matching completed LAST generation')
    cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
    vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
    processor=VideoProcessor(vae_scale_factor=8);codes=torch.load(a.run/'codes.pt',weights_only=True);codec=BCH512()
    source_sha=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
    failed=False
    for condition in CONDITIONS:
        attack=json.loads((a.run/'attacks'/(condition+'.json')).read_text())
        if attack.get('status')!='completed' or attack['source_sha256']!=source_sha:raise ValueError('Require completed attack from this marked video')
        path=a.run/'marked.mp4' if condition=='clean' else a.run/'attacks'/(condition+'.mp4')
        received=load_mp4(path);video_sha=hashlib.sha256(path.read_bytes()).hexdigest();cache={}
        for variant,(reader,scan) in VARIANTS.items():
            target=a.output/f'{condition}-{variant}.json'
            if target.exists():
                prior=json.loads(target.read_text())
                if prior.get('video_sha256')!=video_sha:raise ValueError('Existing ablation uses another video')
                if prior.get('status')=='completed':continue
                target.rename(target.with_suffix(f'.failed-{time.time_ns()}.json'))
            row=dict(status='running',variant=variant,condition=condition,video_id=attack['video_id'],video_sha256=video_sha,source_sha256=source_sha,scope='Reader ablation; features reused within condition, not a timing benchmark')
            try:
                soft,meta=extract(received,vae,processor,a.family,codes,reader,scan,cache)
                prediction,dec=codec.decode(soft.numpy())
                # Truth is used only after the reader has returned.
                truth=np.load(a.run/'message.npy')
                row.update(status='completed',correct_bits=int((prediction==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(prediction,truth)),**dec,**meta)
            except Exception:row.update(status='failed',error=traceback.format_exc());failed=True
            temp=target.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2));temp.replace(target)
            print(condition,variant,row['status'],row.get('correct_bits'),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
