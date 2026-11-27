"""Attack evaluation from exported MP4; secret truth is used only after extraction."""
import argparse, hashlib, json, os, time, traceback
from pathlib import Path
import numpy as np
import torch
from .video import load_mp4, export_mp4
from .temporal import segments, windows
from .attacks import attacked
from .elmc import feature
from .ccta import align
from .coding import BCH512
from .report import CONDITIONS

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

def candidate_features(frames, vae, processor, family,reader='ccta',scan=True,feature_cache=None):
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
    return values,nodes

def extract(frames, vae, processor, family, codes,reader='ccta',scan=True,feature_cache=None):
    values,nodes=candidate_features(frames,vae,processor,family,reader,scan,feature_cache)
    if reader=='received':
        soft=sum((codes[g].float()@value for g,value in enumerate(values)),torch.zeros(codes.shape[1]))
        return soft,{'route':'received_order','groups':len(nodes)}
    soft, alignment = align(values,nodes,codes,reader=reader)
    alignment['candidate_windows'] = len(nodes)
    return soft, alignment

def extract_lfg(frames,vae,processor,family,key,prepared_carriers=None):
    from .lfg import align_received_frames,scores
    with torch.inference_mode():
        x=processor.preprocess_video([align_received_frames(frames)]).to('cuda',torch.float32)
        z=vae.encode(x).latent_dist.mode()
        if family=='hunyuan':z=z*vae.config.scaling_factor
        else:
            mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
            std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1)
            z=(z-mean)/std
        return scores(z,key,prepared_carriers),{'route':'lfg_received_order','groups':16}

def evaluation_directory(run,map_seed):
    if map_seed not in range(5):raise ValueError('Expected map seed0..4')
    return Path(run)/('attacks' if map_seed==0 else f'attacks-map-{map_seed}')

def check_cached(row,video_id,method,source_sha,map_seed):
    if row.get('video_id')!=video_id or row.get('method',method)!=method or row.get('source_sha256')!=source_sha or row.get('map_seed',0)!=map_seed:
        raise ValueError('Existing attack receipt belongs to another source/method/map')

def verify_received(row,path):
    expected=row.get('received_sha256')
    if not expected or not Path(path).is_file() or hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
        raise ValueError('Received MP4 missing, changed, or not fingerprinted; audit before reuse')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--model-dir',required=True);p.add_argument('--video-id',required=True);p.add_argument('--family',choices=['hunyuan','wan22'],required=True)
    p.add_argument('--map-seed',type=int,choices=range(5),default=0)
    p.add_argument('--condition', choices=CONDITIONS,
                   help='Evaluate a single condition. Omit to evaluate all seven.')
    a=p.parse_args()
    os.umask(0o077)
    vae = None
    generation=json.loads((a.run/'receipt.json').read_text());method=generation.get('method','last')
    if generation.get('status')!='completed' or generation.get('family')!=a.family:raise ValueError('Require completed generation for matching family')
    if method not in ('last','lfg','lfg-c'):raise ValueError('Unsupported method in generation receipt')
    source_sha=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
    if generation.get('marked_sha256')!=source_sha:raise ValueError('Generation MP4 changed')
    directory=evaluation_directory(a.run,a.map_seed);directory.mkdir(exist_ok=True);failed=False
    for name in ((a.condition,) if a.condition else CONDITIONS):
        receipt=directory/(name+'.json')
        if receipt.exists():
            prior=json.loads(receipt.read_text());check_cached(prior,a.video_id,method,source_sha,a.map_seed)
            if prior.get('condition')!=name:raise ValueError('Cached condition mismatch')
            if prior.get('status')=='completed':
                verify_received(prior,a.run/'marked.mp4' if name=='clean' else directory/(name+'.mp4'))
                print(name, 'verified cached result', prior.get('correct_bits'), flush=True)
                continue
        if vae is None:
            from diffusers import AutoencoderKLHunyuanVideo, AutoencoderKLWan
            from diffusers.video_processor import VideoProcessor
            torch.set_num_threads(4)
            torch.cuda.set_per_process_memory_fraction(.20)
            cls = AutoencoderKLHunyuanVideo if a.family == 'hunyuan' else AutoencoderKLWan
            vae = cls.from_pretrained(a.model_dir, subfolder='vae', torch_dtype=torch.float32,
                                      local_files_only=True).to('cuda')
            vae.enable_tiling()
            processor = VideoProcessor(vae_scale_factor=8)
            codes = torch.load(a.run/'codes.pt', weights_only=True)
            truth = np.load(a.run/'message.npy')
            codec = BCH512()
            source = load_mp4(a.run/'marked.mp4')
        if receipt.exists():receipt.rename(directory/(name+f'.previous-{time.time_ns()}.json'))
        started=time.time();row={'condition':name,'video_id':a.video_id,'status':'running','source_sha256':source_sha,'map_seed':a.map_seed}
        try:
            edited,mapping=attacked(source,name,a.video_id,seed=a.map_seed if name in ('drop','insert','clip') else 0)
            if name=='clean':path=a.run/'marked.mp4'
            else:
                path=directory/(name+'.mp4');row['codec_command']=export_mp4(edited,path,crf=28 if name=='compression' else 18)
            # Mapping is evaluator metadata; it is never passed to extract().
            row['attack_map']=mapping;row['received_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();received=load_mp4(path)
            if method=='lfg':soft,meta=extract_lfg(received,vae,processor,a.family,(a.run/'secret.key').read_bytes())
            else:soft,meta=extract(received,vae,processor,a.family,codes)
            verify_received(row,path)
            row['method']=method
            prediction,dec=codec.decode(soft.numpy());raw=(soft.numpy()>0).astype(np.uint8)
            row.update(status='completed',correct_bits=int((prediction==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(prediction,truth)),raw_information_correct=int((raw[:512]==truth).sum()),coded_correct=int((raw==codec.encode(truth)).sum()),coded_total=592,frames=len(received),**dec,**meta)
        except Exception:row.update(status='failed',error=traceback.format_exc());failed=True
        row['seconds']=time.time()-started
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2));temp.replace(receipt)
        print(name,row['status'],row.get('correct_bits'),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
