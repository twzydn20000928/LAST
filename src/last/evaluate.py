"""Attack evaluation from exported MP4; secret truth is used only after extraction."""
import argparse, hashlib, json, os, time, traceback
from pathlib import Path
import numpy as np
import torch
from .video import load_mp4, export_mp4
from .temporal import attack_map, segments, windows
from .elmc import feature
from .ccta import align
from .coding import BCH512

def attacked(frames, name, video_id, seed=0):
    from PIL import Image
    import cv2
    digest=hashlib.sha256(f'LAST-pixels-v1:{video_id}:{name}:{seed}'.encode()).digest()
    rng=np.random.Generator(np.random.PCG64(int.from_bytes(digest,'big')))
    if name in ('clean','compression'):return frames, None
    if name in ('drop','clip','insert'):
        mapping=attack_map(video_id,name,seed,frames=len(frames))
        shape=np.asarray(frames[0]).shape
        # The paper does not specify the noise-frame distribution; fix uniform RGB8.
        return [frames[i] if i>=0 else Image.fromarray(rng.integers(0,256,shape,dtype=np.uint8)) for i in mapping], mapping
    output=[]
    for f in frames:
        x=np.asarray(f)
        if name=='noise':x=np.rint(np.clip(x/255.+rng.normal(0,.05,x.shape),0,1)*255).astype(np.uint8)
        elif name=='blur':x=cv2.GaussianBlur(x,(5,5),1)
        else:raise ValueError(name)
        output.append(Image.fromarray(x))
    return output,None

def reader_nodes(frames,reader='ccta',scan=True):
    if reader not in ('ccta','energy','received'):raise ValueError('Unknown reader')
    if reader=='received':
        # The first received frame is treated as the causal prefix, without
        # estimating its original identity. Extra frames are clipped, missing
        # complete groups remain absent; a short final group repeats its last frame.
        nodes=[]
        hi=min(len(frames)-1,64)
        for start in range(1,hi+1,4):
            end=min(start+3,hi);indices=list(range(start,end+1))
            nodes.append(dict(start=start,end=end,segment=0,indices=indices+[end]*(4-len(indices)),padded=end-start<3))
        return nodes
    return list(windows(segments(frames),scan=scan))

def extract(frames, vae, processor, family, codes,reader='ccta',scan=True,feature_cache=None):
    nodes=reader_nodes(frames,reader,scan);features=[]
    with torch.inference_mode():
        for node in nodes:
            cache_key=tuple(node['indices'])
            if feature_cache is not None and cache_key in feature_cache:
                features.append(feature_cache[cache_key]);continue
            content=[frames[node['indices'][0]]]+[frames[i] for i in node['indices']]
            x=processor.preprocess_video([content]).to('cuda',torch.float32)
            z=vae.encode(x).latent_dist.mode()
            if family=='hunyuan':z=z*vae.config.scaling_factor
            else:
                mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
                std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1)
                z=(z-mean)/std
            value=feature(z).cpu();features.append(value)
            if feature_cache is not None:feature_cache[cache_key]=value
    values=torch.stack(features) if features else torch.empty(0,1776)
    if reader=='received':
        soft=sum((codes[g].float()@value for g,value in enumerate(features)),torch.zeros(codes.shape[1]))
        return soft,{'route':'received_order','groups':len(nodes)}
    return align(values,nodes,codes,reader=reader)

def extract_lfg(frames,vae,processor,family,key):
    from .lfg import align_received_frames,scores
    with torch.inference_mode():
        x=processor.preprocess_video([align_received_frames(frames)]).to('cuda',torch.float32)
        z=vae.encode(x).latent_dist.mode()
        if family=='hunyuan':z=z*vae.config.scaling_factor
        else:
            mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
            std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1)
            z=(z-mean)/std
        return scores(z,key),{'route':'lfg_received_order','groups':16}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--model-dir',required=True);p.add_argument('--video-id',required=True);p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    os.umask(0o077);torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(.20)
    from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
    from diffusers.video_processor import VideoProcessor
    cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
    vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
    processor=VideoProcessor(vae_scale_factor=8)
    codes=torch.load(a.run/'codes.pt',weights_only=True);truth=np.load(a.run/'message.npy');codec=BCH512()
    method=json.loads((a.run/'receipt.json').read_text()).get('method','last')
    if method not in ('last','lfg'):raise ValueError('Unsupported method in generation receipt')
    source=load_mp4(a.run/'marked.mp4');directory=a.run/'attacks';directory.mkdir(exist_ok=True)
    for name in ['clean','noise','compression','blur','drop','insert','clip']:
        receipt=directory/(name+'.json')
        if receipt.exists() and json.loads(receipt.read_text()).get('status')=='completed':continue
        if receipt.exists():receipt.rename(directory/(name+f'.previous-{time.time_ns()}.json'))
        started=time.time();row={'condition':name,'video_id':a.video_id,'status':'running','source_sha256':hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()}
        try:
            edited,mapping=attacked(source,name,a.video_id)
            if name=='clean':path=a.run/'marked.mp4'
            else:
                path=directory/(name+'.mp4');row['codec_command']=export_mp4(edited,path,crf=28 if name=='compression' else 18)
            # Mapping is evaluator metadata; it is never passed to extract().
            row['attack_map']=mapping;received=load_mp4(path)
            if method=='lfg':soft,meta=extract_lfg(received,vae,processor,a.family,(a.run/'secret.key').read_bytes())
            else:soft,meta=extract(received,vae,processor,a.family,codes)
            row['method']=method
            prediction,dec=codec.decode(soft.numpy());raw=(soft.numpy()>0).astype(np.uint8)
            row.update(status='completed',correct_bits=int((prediction==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(prediction,truth)),raw_information_correct=int((raw[:512]==truth).sum()),coded_correct=int((raw==codec.encode(truth)).sum()),coded_total=592,frames=len(received),**dec,**meta)
        except Exception:row.update(status='failed',error=traceback.format_exc())
        row['seconds']=time.time()-started
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2));temp.replace(receipt)
        print(name,row['status'],row.get('correct_bits'),flush=True)

if __name__=='__main__':main()
