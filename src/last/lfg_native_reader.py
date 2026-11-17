"""Reader-only native-Haar LFG + CCTA control on existing attacked videos."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .lfg import carriers,lowpass
from .ccta import align_correlations
from .coding import BCH512
from .temporal import segments,windows
from .video import load_mp4


def extract(frames,vae,processor,family,key):
    nodes=list(windows(segments(frames),group_frames=8));features=[]
    with torch.inference_mode():
        for node in nodes:
            selected=[frames[node['indices'][0]]]+[frames[i] for i in node['indices']]
            x=processor.preprocess_video([selected]).to('cuda',torch.float32)
            z=vae.encode(x).latent_dist.mode()
            if family=='hunyuan':z=z*vae.config.scaling_factor
            else:
                mean=torch.as_tensor(vae.config.latents_mean,device=z.device).view(1,16,1,1,1)
                std=torch.as_tensor(vae.config.latents_std,device=z.device).view(1,16,1,1,1);z=(z-mean)/std
            if z.shape!=(1,16,3,64,64):raise ValueError('Native Haar-pair reader requires nine-frame VAE encoding')
            features.append(lowpass(z[:,:,1:]).flatten().cpu())
    if not features:return torch.zeros(592),dict(route='no_evidence',groups=0)
    feature=torch.stack(features);corr=torch.empty(len(nodes),8,592)
    for pair in range(8):
        raw=feature@carriers(key,pair).float().T/16384
        corr[:,pair]=raw.reshape(len(nodes),2,592).mean(1)
    soft,meta=align_correlations(corr,nodes,group_frames=8)
    return soft,dict(**meta,native_haar_pairs=8,group_frames=8,candidate_windows=len(nodes))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    generation=json.loads((a.run/'receipt.json').read_text())
    if generation.get('status')!='completed' or generation.get('method')!='lfg' or generation.get('family')!=a.family:
        raise ValueError('Require completed original LFG generation')
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    record=dict(status='running',scope='Reader-only native LFG+CCTA; original writer and attack MP4s unchanged',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=[])
    start=time.monotonic()
    def save():
        record['seconds']=time.monotonic()-start
        (a.output/'receipt.json').write_text(json.dumps(record,indent=2))
    save()
    try:
        from diffusers import AutoencoderKLHunyuanVideo,AutoencoderKLWan
        from diffusers.video_processor import VideoProcessor
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(.20)
        cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True).to('cuda');vae.enable_tiling()
        processor=VideoProcessor(vae_scale_factor=8);codec=BCH512();key=(a.run/'secret.key').read_bytes()
        original=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
        for name in ('clean','noise','compression','blur','drop','insert','clip'):
            prior=json.loads((a.run/'attacks'/(name+'.json')).read_text())
            if prior.get('status')!='completed' or prior['source_sha256']!=original:raise ValueError('Incomplete or mismatched original attack')
            video=a.run/'marked.mp4' if name=='clean' else a.run/'attacks'/(name+'.mp4')
            sha=hashlib.sha256(video.read_bytes()).hexdigest()
            if sha!=prior['received_sha256']:raise ValueError('Attack MP4 changed')
            soft,meta=extract(load_mp4(video),vae,processor,a.family,key)
            prediction,dec=codec.decode(soft.numpy())
            # Truth is used only after readout, never by candidate alignment.
            truth=np.load(a.run/'message.npy')
            np.save(a.output/(name+'_prediction_private.npy'),prediction)
            record['rows'].append(dict(condition=name,correct_bits=int((prediction==truth).sum()),total_bits=512,
                                       exact_message=bool(np.array_equal(prediction,truth)),received_sha256=sha,**dec,**meta))
            save();print(name,record['rows'][-1]['correct_bits'],flush=True)
        record['status']='completed';save()
    except BaseException:record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
