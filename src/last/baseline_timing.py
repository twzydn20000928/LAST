"""Warm native Hunyuan baseline readout timing, including MP4 decoding and SGO."""
import argparse,hashlib,importlib,json,os,statistics
from pathlib import Path
from .reader_timing import measure,require_exclusive


class NativePipeline:
    """Match the native extraction adapter without per-step receipt disk IO."""
    def __init__(self,pipe,mode,dtype):
        self.pipe=pipe;self.mode=mode;self.dtype=dtype;self.calls=0
    def __getattr__(self,name):return getattr(self.pipe,name)
    def __call__(self,*args,**kwargs):
        if self.mode=='t2v':kwargs.pop('image',None)
        kwargs['latents']=kwargs['latents'].to(dtype=self.dtype)
        self.calls+=1
        return self.pipe(*args,**kwargs)


def recover_frames(frames,method,temporal,watermark,pipe,align_frames):
    if not temporal and len(frames)!=65:raise ValueError('Select temporal recovery for changed length')
    if temporal:
        frames=watermark.segment_group_ordering(frames,65,True,True,pipe) if method=='sigmark' else align_frames(frames,65)
    if len(frames)!=65 or any(f is None for f in frames):raise ValueError('Recovery did not produce65valid frames')
    return frames


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['sigmark','videoshield','videomark'],required=True)
    p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    for name in ('video','state','model-dir','upstream','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest',type=Path,default=Path('configs/sigmark_source_manifest.json'))
    p.add_argument('--protocol',choices=['main','supplement'],required=True)
    p.add_argument('--temporal',action='store_true')
    a=p.parse_args();os.umask(0o077)
    if a.output.exists():raise ValueError('Use a new output file')
    require_exclusive()
    import torch
    import numpy as np
    from diffusers import HunyuanVideoPipeline,HunyuanVideoImageToVideoPipeline,AutoencoderKLHunyuanVideo
    from .baseline_probe import load_class
    from .baseline_extract import validate_prediction
    from .video import load_mp4
    torch.set_num_threads(4)
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    inputs={name:digest(getattr(a,name)) for name in ('video','state','manifest')}
    sources={f.name:digest(f) for f in Path(__file__).parent.glob('*.py')}
    manifest=json.loads(a.manifest.read_text());cls=load_class(a.method,a.upstream,manifest)
    wm=cls(video_h=512,video_w=512,video_f=65,latent_c=16,vae_scale_factor_spatial=8,vae_scale_factor_temporal=4,ch_factor=2,hw_factor=8,fr_factor=16,batch_size=1,seed=0,dtype=torch.bfloat16,device='cuda',maintained_info_path=str(a.state))
    vae=AutoencoderKLHunyuanVideo.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True);vae.enable_tiling()
    pc=HunyuanVideoImageToVideoPipeline if a.mode=='i2v' else HunyuanVideoPipeline
    pipe=pc.from_pretrained(a.model_dir,vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
    scheduler=importlib.import_module('models.schedulers').FlowMatchEulerDiscreteInverseScheduler
    pipe.scheduler=scheduler.from_config(pipe.scheduler.config,shift=7)
    pipe.enable_sequential_cpu_offload(device='cuda:0')
    pipe.set_progress_bar_config(disable=True)
    adapter=NativePipeline(pipe,a.mode,torch.bfloat16)
    align_frames=importlib.import_module('utils.video_utils').align_frames
    diagnostics=[];first_prediction=None
    def operation():
        nonlocal first_prediction
        torch.manual_seed(0);torch.cuda.manual_seed_all(0)
        frames=load_mp4(a.video)
        if not frames or any(f.size!=(512,512) for f in frames):raise ValueError('Expected512-square video')
        received=len(frames);adapter.calls=0
        with torch.inference_mode():
            frames=recover_frames(frames,a.method,a.temporal,wm,adapter,align_frames)
            pixels=pipe.video_processor.preprocess_video([frames]).to('cuda',torch.float32)
            encoded=pipe.vae.encode(pixels).latent_dist.mode()*pipe.vae.config.scaling_factor
            kwargs=dict(prompt=[''],guidance_scale=6,num_inference_steps=50,num_frames=65,latents=encoded,output_type='latent',return_dict=False,height=512,width=512)
            if a.mode=='i2v':kwargs['image']=[frames[0]]
            prediction=validate_prediction(wm.extract_watermark(adapter(**kwargs)[0]))
        if first_prediction is None:first_prediction=prediction.copy()
        diagnostics.append(dict(received_frames=received,inversion_calls=adapter.calls,same_prediction_as_first=bool(np.array_equal(prediction,first_prediction))))
    repeats=2 if a.protocol=='main' else 5
    times=measure(operation,torch.cuda.synchronize,require_exclusive,2,repeats)
    if inputs!={name:digest(getattr(a,name)) for name in inputs}:raise ValueError('Inputs changed during timing')
    if sources!={f.name:digest(f) for f in Path(__file__).parent.glob('*.py')}:raise ValueError('Source changed during timing')
    result=dict(status='completed',method=a.method,family='hunyuan',mode=a.mode,protocol=a.protocol,temporal=a.temporal,
                warmups=2,repeats=repeats,seconds=times,mean_seconds=statistics.mean(times),median_seconds=statistics.median(times),
                reported_seconds=statistics.mean(times) if a.protocol=='main' else statistics.median(times),
                received_sha256=inputs['video'],input_sha256=inputs,source_sha256=sources,upstream_commit=manifest['commit'],
                gpu=torch.cuda.get_device_name(0),torch_version=torch.__version__,cuda_version=torch.version.cuda,
                diagnostics_including_warmups=diagnostics,offload='sequential CPU offload; transfers inside timing',
                includes=['MP4 decoding','native temporal recovery when requested','VAE encode','all diffusion inversions','native message decoding','seed reset and lightweight diagnostics'],
                excludes=['model loading','one-time native key/state setup','export','per-step receipt writes'],
                scope='Single-video native extraction timing; not generation overhead or full comparison',
                concurrency_check='Other compute PIDs rejected before/after every read; requires external exclusive reservation')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status='completed',reported_seconds=result['reported_seconds'])))


if __name__=='__main__':main()
