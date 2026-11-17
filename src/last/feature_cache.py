"""Acquire key-free candidate features for controlled reader comparisons."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(folder,video):
    folder=Path(folder);record=json.loads((folder/'receipt.json').read_text())
    if record.get('status')!='completed' or record.get('video_sha256')!=sha(video):
        raise ValueError('Incomplete feature cache or changed source video')
    for name in ('features.npy','nodes.json'):
        if sha(folder/name)!=record.get('files_sha256',{}).get(name):
            raise ValueError('Feature cache artifact changed')
    values=np.load(folder/'features.npy',allow_pickle=False)
    nodes=json.loads((folder/'nodes.json').read_text())
    if values.shape!=(len(nodes),1776) or not np.isfinite(values).all():
        raise ValueError('Invalid candidate feature array')
    return values,nodes,record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('video','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True)
    p.add_argument('--reader',choices=['ccta','received'],default='ccta')
    p.add_argument('--no-scan',action='store_true')
    a=p.parse_args();os.umask(0o077)
    a.output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).parent
    sources={name:sha(source/name) for name in ('feature_cache.py','evaluate.py','elmc.py','temporal.py','video.py')}
    model_files=sorted(f for f in (a.model_dir/'vae').iterdir() if f.is_file() and f.suffix in ('.json','.safetensors','.bin'))
    if not model_files:raise ValueError('Missing local VAE files')
    model_hashes={f.name:sha(f) for f in model_files}
    record=dict(status='running',family=a.family,reader=a.reader,scan=not a.no_scan,
                video_sha256=sha(a.video),source_sha256=sources,vae_files_sha256=model_hashes,
                scope='Key-free normalized candidate features; no decoded message or score; not a timing measurement')
    start=time.monotonic()
    def save():
        record['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(a.output/'receipt.json')
    save()
    try:
        import torch
        from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
        from diffusers.video_processor import VideoProcessor
        from .evaluate import candidate_features
        from .video import load_mp4
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(.20)
        frames=load_mp4(a.video)
        if not frames or any(np.asarray(f).shape!=(512,512,3) for f in frames):
            raise ValueError('Expected nonempty512-square RGB video')
        cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
        values,nodes=candidate_features(frames,vae,VideoProcessor(vae_scale_factor=8),a.family,a.reader,not a.no_scan)
        if (sha(a.video)!=record['video_sha256'] or any(sha(source/n)!=h for n,h in sources.items())
                or any(sha(a.model_dir/'vae'/n)!=h for n,h in model_hashes.items())):
            raise ValueError('Video, feature implementation or VAE changed during acquisition')
        np.save(a.output/'features.npy',values.numpy(),allow_pickle=False)
        (a.output/'nodes.json').write_text(json.dumps(nodes,indent=2))
        record.update(status='completed',frames=len(frames),candidates=len(nodes),
                      files_sha256={n:sha(a.output/n) for n in ('features.npy','nodes.json')})
        save()
    except BaseException:
        record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
