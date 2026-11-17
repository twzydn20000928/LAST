"""Attack-map-assisted diagnostic reader; never a deployable blind extractor."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .elmc import feature
from .coding import BCH512
from .video import load_mp4


def oracle_nodes(mapping):
    locations={}
    for received,original in enumerate(mapping):
        if not isinstance(original,int) or not -1<=original<=64:raise ValueError('Invalid original frame identity')
        if original>0:locations.setdefault(original,received)
    result=[]
    for group in range(16):
        targets=list(range(1+4*group,5+4*group))
        present=[i for i in targets if i in locations]
        if not present:continue
        # Never borrow pixels from a clean/original video. Fill missing slots
        # using the nearest surviving frame in this group, earlier on a tie.
        originals=[min(present,key=lambda q:(abs(q-i),q)) for i in targets]
        result.append(dict(group=group,indices=[locations[i] for i in originals],
                           observed=len(present),filled=4-len(present)))
    return result


def extract(frames,mapping,vae,processor,family,codes):
    if len(frames)!=len(mapping):raise ValueError('Mapping length differs from received video')
    nodes=oracle_nodes(mapping);rows=[]
    with torch.inference_mode():
        for node in nodes:
            content=[frames[node['indices'][0]]]+[frames[i] for i in node['indices']]
            x=processor.preprocess_video([content]).to('cuda',torch.float32)
            z=vae.encode(x).latent_dist.mode()
            if family=='hunyuan':z=z*vae.config.scaling_factor
            else:
                mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
                std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1);z=(z-mean)/std
            correlation=codes[node['group']].float()@feature(z).cpu()
            rows.append(correlation/correlation.norm().clamp_min(1e-8))
    soft=torch.stack(rows).mean(0) if rows else torch.zeros(592)
    return soft,dict(route='oracle_attack_map',groups=len(nodes),
                     complete_groups=sum(n['observed']==4 for n in nodes),
                     filled_slots=sum(n['filled'] for n in nodes),missing_groups=16-len(nodes))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    generation=json.loads((a.run/'receipt.json').read_text())
    if generation.get('status')!='completed' or generation.get('family')!=a.family or generation.get('method') not in ('last','lfg-c'):
        raise ValueError('Require completed shared-codebook generation')
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    state=dict(status='running',scope='Oracle uses true attack map; not blind extraction or primary performance',
               fill_policy='Nearest surviving same-group frame; earlier tie; absent groups omitted; inserted/duplicate frames excluded',
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=[])
    start=time.monotonic()
    def save():
        state['seconds']=time.monotonic()-start
        (a.output/'receipt.json').write_text(json.dumps(state,indent=2))
    save()
    try:
        from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
        from diffusers.video_processor import VideoProcessor
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(.20)
        cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
        processor=VideoProcessor(vae_scale_factor=8);codes=torch.load(a.run/'codes.pt',weights_only=True);codec=BCH512()
        source_sha=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
        for name in ('clean','noise','compression','blur','drop','insert','clip'):
            receipt=a.run/'attacks'/(name+'.json');attack=json.loads(receipt.read_text())
            if attack.get('status')!='completed' or attack['source_sha256']!=source_sha:raise ValueError('Mismatched source attack')
            video=a.run/'marked.mp4' if name=='clean' else a.run/'attacks'/(name+'.mp4')
            sha=hashlib.sha256(video.read_bytes()).hexdigest()
            if attack.get('received_sha256',sha)!=sha:raise ValueError('Attack video changed')
            frames=load_mp4(video);mapping=attack['attack_map']
            if mapping is None:
                if len(frames)!=65:raise ValueError('No map for changed-length video')
                mapping=list(range(65))
            soft,meta=extract(frames,mapping,vae,processor,a.family,codes)
            prediction,dec=codec.decode(soft.numpy());truth=np.load(a.run/'message.npy')
            state['rows'].append(dict(condition=name,correct_bits=int((prediction==truth).sum()),total_bits=512,
                                      raw_information_correct=int(((soft.numpy()[:512]>0)==truth).sum()),
                                      exact_message=bool(np.array_equal(prediction,truth)),
                                      received_sha256=sha,attack_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),**meta,**dec))
            save();print(name,state['rows'][-1]['correct_bits'],flush=True)
        state['status']='completed';save()
    except BaseException:state.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
