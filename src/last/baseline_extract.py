"""Native baseline inversion/readout, without an evaluation-message input."""
import argparse,hashlib,importlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from .baseline_probe import load_class
from .video import load_mp4
from .native_model_adapter import normalize_endpoint,SGOVAE,native_call_kwargs

def validate_prediction(value):
    result=np.asarray(value)
    if result.size!=512 or not np.isin(result,[0,1]).all():
        raise ValueError('Native decoder did not return512binary information bits')
    return result.astype(np.uint8).reshape(-1)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['videoshield','videomark','sigmark'],required=True)
    p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],default='hunyuan')
    for name in ['upstream','model-dir','video','state','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest',type=Path,default=Path('configs/sigmark_source_manifest.json'))
    p.add_argument('--temporal',action='store_true',help='Apply nativeSGO for SIGMark; native length alignment for other baselines')
    p.add_argument('--memory-gib',type=float,default=8)
    a=p.parse_args();os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    start=time.monotonic();receipt=dict(status='starting',method=a.method,family=a.family,mode=a.mode,scope='Native extraction, no ground-truth message provided',temporal=a.temporal,inversion_calls=[])
    def save():
        receipt['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(receipt,indent=2));temp.replace(a.output/'receipt.json')
    try:
        torch.set_num_threads(4)
        manifest=json.loads(a.manifest.read_text());cls=load_class(a.method,a.upstream,manifest)
        # Pickle is native upstream state: accept only the user's own trusted file.
        wm=cls(video_h=512,video_w=512,video_f=65,latent_c=16,vae_scale_factor_spatial=8,vae_scale_factor_temporal=4,ch_factor=2,hw_factor=8,fr_factor=16,batch_size=1,seed=0,dtype=torch.bfloat16,device='cuda',maintained_info_path=str(a.state))
        receipt.update(upstream_commit=manifest['commit'],video_sha256=hashlib.sha256(a.video.read_bytes()).hexdigest(),state_sha256=hashlib.sha256(a.state.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        frames=load_mp4(a.video)
        if not frames or any(f.size!=(512,512) for f in frames):raise ValueError('Expected nonempty512-square received video')
        receipt['received_frames']=len(frames)
        if not a.temporal and len(frames)!=65:raise ValueError('Length changed; explicitly select temporal recovery')
        from diffusers import HunyuanVideoPipeline,HunyuanVideoImageToVideoPipeline,AutoencoderKLHunyuanVideo,WanPipeline,WanImageToVideoPipeline,AutoencoderKLWan
        native_scheduler=importlib.import_module('models.schedulers').FlowMatchEulerDiscreteInverseScheduler
        torch.cuda.set_per_process_memory_fraction(a.memory_gib*1024**3/torch.cuda.get_device_properties(0).total_memory)
        vae_cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=vae_cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True);vae.enable_tiling()
        pipeline_cls=(HunyuanVideoImageToVideoPipeline if a.mode=='i2v' else HunyuanVideoPipeline) if a.family=='hunyuan' else (WanImageToVideoPipeline if a.mode=='i2v' else WanPipeline)
        pipe=pipeline_cls.from_pretrained(a.model_dir,vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        pipe.scheduler=native_scheduler.from_config(pipe.scheduler.config,shift=7 if a.family=='hunyuan' else 5)
        receipt['inversion_settings']=dict(scheduler='upstream FlowMatchEulerDiscreteInverseScheduler',steps=50,shift=7 if a.family=='hunyuan' else 5,guidance=6 if a.family=='hunyuan' else 5,wan_scope='Explicit inversion adaptation; UniPC generation unchanged; real-video validation pending' if a.family=='wan22' else None)
        receipt['adapter_source_sha256']=hashlib.sha256((Path(__file__).parent/'native_model_adapter.py').read_bytes()).hexdigest()
        pipe.enable_sequential_cpu_offload(device='cuda:0')
        def callback(pipeline,step,timestep,kw):receipt['last_step']=int(step);save();return kw
        class MeasuredPipeline:
            @property
            def vae(self):return SGOVAE(pipe.vae) if a.family=='wan22' else pipe.vae
            def __getattr__(self,name):return getattr(pipe,name)
            def __call__(self,*args,**kw):
                # Upstream SGO supplies an image even with T2V; that pipeline has no image argument.
                kw=native_call_kwargs(kw,a.family,a.mode)
                kw['latents']=kw['latents'].to(dtype=torch.bfloat16)
                item=dict(frames=kw.get('num_frames'),steps=kw.get('num_inference_steps'),status='running');receipt['inversion_calls'].append(item);save();tick=time.monotonic()
                try:
                    result=pipe(*args,callback_on_step_end=callback,**kw);item['status']='completed';return result
                finally:item['seconds']=time.monotonic()-tick;save()
        measured=MeasuredPipeline()
        torch.manual_seed(0);torch.cuda.manual_seed_all(0)
        with torch.inference_mode():
            if a.temporal:
                receipt['status']='temporal_recovery';save()
                if a.method=='sigmark':frames=wm.segment_group_ordering(frames,65,True,True,measured)
                else:frames=importlib.import_module('utils.video_utils').align_frames(frames,65)
            if len(frames)!=65 or any(f is None for f in frames):raise ValueError('Native recovery did not produce65valid frames')
            receipt['status']='final_inversion';save()
            pixels=pipe.video_processor.preprocess_video([frames]).to('cuda',torch.float32)
            encoded=normalize_endpoint(pipe.vae.encode(pixels).latent_dist.mode(),pipe.vae.config,a.family)
            kw=dict(prompt=[''],guidance_scale=6,num_inference_steps=50,num_frames=65,latents=encoded,output_type='latent',return_dict=False,height=512,width=512)
            if a.mode=='i2v':kw['image']=[frames[0]]
            initial=measured(**kw)[0]
            receipt['status']='decoding';save()
            prediction=validate_prediction(wm.extract_watermark(initial))
        (a.output/'decoded.bin').write_bytes(np.packbits(prediction).tobytes())
        receipt.update(status='completed_extraction',information_bits=512,peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3)
    except Exception:
        receipt.update(status='failed',error=traceback.format_exc());raise
    finally:save()

if __name__=='__main__':main()

