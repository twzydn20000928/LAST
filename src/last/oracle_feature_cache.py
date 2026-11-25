"""True-map-assisted feature acquisition for the controlled, non-blind diagnostic."""
import argparse,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .feature_cache import sha
from .oracle_reader import oracle_nodes
from .elmc import feature


def received_digest(attack, video):
    if "received_sha256" in attack:
        return attack["received_sha256"]
    if (attack.get("condition") == "clean" and attack["attack_map"] is None
            and attack.get("frames") == 65 and video.name == "marked.mp4"
            and attack.get("video_id") == video.parent.name):
        return attack.get("source_sha256")
    return None


def acquire(frames,mapping,vae,processor,family,device='cuda'):
    if len(frames)!=len(mapping):raise ValueError('Map length differs from received video')
    if family not in ('hunyuan','wan22'):raise ValueError('Unknown VAE family')
    nodes=oracle_nodes(mapping);rows=[]
    with torch.inference_mode():
        for node in nodes:
            content=[frames[node['indices'][0]]]+[frames[i] for i in node['indices']]
            x=processor.preprocess_video([content]).to(device,torch.float32)
            z=vae.encode(x).latent_dist.mode()
            if family=='hunyuan':z=z*vae.config.scaling_factor
            else:
                mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
                std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1)
                z=(z-mean)/std
            rows.append(feature(z).cpu())
    return torch.stack(rows) if rows else torch.empty((0,1776)),nodes


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('video','attack-receipt','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True)
    a=p.parse_args();os.umask(0o077)
    attack=json.loads(a.attack_receipt.read_text())
    if attack.get('status')!='completed' or received_digest(attack,a.video)!=sha(a.video):
        raise ValueError('Require completed attack receipt bound to actual received MP4')
    source=Path(__file__).parent
    sources={name:sha(source/name) for name in ('oracle_feature_cache.py','oracle_reader.py','elmc.py','video.py','feature_cache.py')}
    model_files=sorted(f for f in (a.model_dir/'vae').iterdir() if f.is_file() and f.suffix in ('.json','.safetensors','.bin'))
    if not model_files:raise ValueError('Missing local VAE files')
    model_hashes={f.name:sha(f) for f in model_files}
    inputs={str(a.video):sha(a.video),str(a.attack_receipt):sha(a.attack_receipt)}
    a.output.mkdir(parents=True,exist_ok=False)
    record=dict(status='running',family=a.family,reader='oracle',blind=False,scan=False,
                video_sha256=sha(a.video),input_sha256=inputs,source_sha256=sources,vae_files_sha256=model_hashes,
                scope='True attack-map-assisted diagnostic; no original pixels, keys or message used',
                fill_policy='Nearest surviving same-group frame, earlier tie; duplicate identities once; absent groups omitted')
    start=time.monotonic()
    def save():
        record['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(a.output/'receipt.json')
    save()
    try:
        from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
        from diffusers.video_processor import VideoProcessor
        from .video import load_mp4
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(.20)
        frames=load_mp4(a.video)
        if not frames or any(np.asarray(f).shape!=(512,512,3) for f in frames):raise ValueError('Expected512-square RGB video')
        mapping=attack['attack_map']
        if mapping is None:
            if len(frames)!=65:raise ValueError('Missing map for changed-length video')
            mapping=list(range(65))
        cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
        values,nodes=acquire(frames,mapping,vae,VideoProcessor(vae_scale_factor=8),a.family)
        if (any(sha(Path(n))!=h for n,h in inputs.items()) or any(sha(source/n)!=h for n,h in sources.items())
                or any(sha(a.model_dir/'vae'/n)!=h for n,h in model_hashes.items())):raise ValueError('Input or implementation changed')
        np.save(a.output/'features.npy',values.numpy(),allow_pickle=False)
        (a.output/'nodes.json').write_text(json.dumps(nodes,indent=2))
        record.update(status='completed',frames=len(frames),candidates=len(nodes),
                      files_sha256={n:sha(a.output/n) for n in ('features.npy','nodes.json')})
        save()
    except BaseException:
        record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
