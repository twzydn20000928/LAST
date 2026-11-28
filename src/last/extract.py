"""Blind extraction CLI: video, secret key and frozen VAE only."""
import argparse,hashlib,json,os,time
from pathlib import Path
import numpy as np
import torch
from .carriers import codebook
from .evaluate import extract, extract_lfg
from .video import load_mp4

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method', choices=['last', 'lfg'], default='last')
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--key',type=Path,required=True)
    p.add_argument('--model-dir',required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--include-pre-bch',action='store_true',help='Include the 512 systematic hard decisions in the private prediction file')
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda', help='Device for VAE encoding (default: cuda)')
    p.add_argument('--memory-fraction', type=float, default=0.20,
                   help='Maximum fraction of total GPU memory for the PyTorch allocator (default: 0.20)')
    a=p.parse_args()
    if not 0 < a.memory_fraction <= 1:
        p.error('--memory-fraction must be greater than 0 and at most 1')
    os.umask(0o077);torch.set_num_threads(4)
    started=time.time()
    if os.path.lexists(a.output):
        raise FileExistsError(f'Choose a new output path: {a.output}')
    from .coding import BCH512
    key=a.key.read_bytes()
    if len(key)!=32:raise ValueError('Expected a binary key file containing exactly 32 bytes')
    frames=load_mp4(a.video)
    if any(np.asarray(f).shape!=(512,512,3) for f in frames):raise ValueError('Expected a 512 x 512 RGB video')
    if a.device == 'cuda':
        torch.cuda.set_per_process_memory_fraction(a.memory_fraction)
    from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
    from diffusers.video_processor import VideoProcessor
    cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
    vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to(a.device);vae.enable_tiling()
    processor = VideoProcessor(vae_scale_factor=8)
    if a.method == 'lfg':
        soft, alignment = extract_lfg(frames, vae, processor, a.family, key)
    else:
        soft, alignment = extract(frames, vae, processor, a.family, torch.from_numpy(codebook(key)))
    bits,decoder=BCH512().decode(soft.numpy())
    result=dict(schema_version=1,device=a.device,method=a.method,information_bits=512,message_hex=np.packbits(bits,bitorder='big').tobytes().hex(),family=a.family,video_sha256=hashlib.sha256(a.video.read_bytes()).hexdigest(),frames=len(frames),seconds=time.time()-started,**decoder,**alignment)
    if a.include_pre_bch:
        result['pre_bch_information_hex'] = np.packbits(soft.numpy()[:512] > 0, bitorder='big').tobytes().hex()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2)
    print(json.dumps({'output':str(a.output),'bch_success':decoder['bch_success'],'route':alignment['route'],'note':'Decoder success is not authentication. No truth message was accessed.'}))
if __name__=='__main__':main()
