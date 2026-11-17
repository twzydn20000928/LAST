"""Evaluate paper reader ablations on identical, already exported attack videos."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .coding import BCH512
from .evaluate import extract,verify_received
from .report import CONDITIONS
from .video import load_mp4

VARIANTS={'full':('ccta',True),'without_cgc':('energy',True),'without_sws':('ccta',False),'without_ccta':('received',False)}


def writer_method(generation,family):
    method=generation.get('method')
    if generation.get('status')!='completed' or method not in ('last','lfg-c') or generation.get('family')!=family:
        raise ValueError('Require matching completed LAST or shared-codebook LFG-C generation')
    return method


def verified_attack(run,condition,generation):
    """Require the exact exported MP4 identified by a completed attack receipt."""
    run=Path(run)
    source_sha=hashlib.sha256((run/'marked.mp4').read_bytes()).hexdigest()
    if generation.get('marked_sha256')!=source_sha:
        raise ValueError('Generation MP4 changed or lacks provenance')
    attack=json.loads((run/'attacks'/(condition+'.json')).read_text())
    if (attack.get('status')!='completed' or attack.get('source_sha256')!=source_sha
        or attack.get('condition')!=condition):
        raise ValueError('Require matching completed attack from this marked video')
    path=run/'marked.mp4' if condition=='clean' else run/'attacks'/(condition+'.mp4')
    verify_received(attack,path)
    return attack,path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['run','model-dir','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(.20)
    from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
    from diffusers.video_processor import VideoProcessor
    generation=json.loads((a.run/'receipt.json').read_text())
    method=writer_method(generation,a.family)
    # Fail before loading a GPU model when historical exports are unverified.
    attacks={condition:verified_attack(a.run,condition,generation) for condition in CONDITIONS}
    hashes={name:hashlib.sha256((Path(__file__).parent/(name+'.py')).read_bytes()).hexdigest()
            for name in ('reader_ablation','evaluate','ccta','temporal','coding','carriers')}
    codes_sha=hashlib.sha256((a.run/'codes.pt').read_bytes()).hexdigest()
    cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
    vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
    processor=VideoProcessor(vae_scale_factor=8);codes=torch.load(a.run/'codes.pt',weights_only=True);codec=BCH512()
    source_sha=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
    failed=False
    for condition in CONDITIONS:
        attack,path=attacks[condition]
        verify_received(attack,path)
        received=load_mp4(path);video_sha=hashlib.sha256(path.read_bytes()).hexdigest();cache={}
        for variant,(reader,scan) in VARIANTS.items():
            target=a.output/f'{condition}-{variant}.json'
            if target.exists():
                prior=json.loads(target.read_text())
                if (prior.get('video_sha256')!=video_sha or prior.get('writer_method')!=method
                    or prior.get('implementation_sha256')!=hashes or prior.get('codes_sha256')!=codes_sha):
                    raise ValueError('Existing ablation has different or unrecorded video/writer/codebook/reader provenance; use a new output directory')
                if prior.get('status')=='completed':continue
                target.rename(target.with_suffix(f'.failed-{time.time_ns()}.json'))
            row=dict(status='running',variant=variant,condition=condition,video_id=attack['video_id'],video_sha256=video_sha,source_sha256=source_sha,writer_method=method,codes_sha256=codes_sha,implementation_sha256=hashes,scope='Reader ablation; features reused within condition, not a timing benchmark')
            try:
                soft,meta=extract(received,vae,processor,a.family,codes,reader,scan,cache)
                verify_received(attack,path)
                if hashlib.sha256((a.run/'codes.pt').read_bytes()).hexdigest()!=codes_sha:
                    raise ValueError('Codebook changed during ablation')
                prediction,dec=codec.decode(soft.numpy())
                # Truth is used only after the reader has returned.
                truth=np.load(a.run/'message.npy')
                row.update(status='completed',correct_bits=int((prediction==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(prediction,truth)),**dec,**meta)
            except Exception:row.update(status='failed',error=traceback.format_exc());failed=True
            temp=target.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2));temp.replace(target)
            print(condition,variant,row['status'],row.get('correct_bits'),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()

