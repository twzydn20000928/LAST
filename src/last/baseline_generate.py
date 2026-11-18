"""Generate a video using a pinned upstream initial-noise watermark.

Generation only: this command does not claim extraction or benchmark completion.
Private native state is needed by the corresponding baseline reader.
"""
import argparse,hashlib,json,os,time,traceback
from io import BytesIO
from pathlib import Path
import numpy as np
import torch
from .baseline_probe import load_class
from .video import export_mp4,load_mp4


def denormalize_endpoint(z,config,family):
    if family=='hunyuan':return z/config.scaling_factor
    if family!='wan22':raise ValueError('Unknown VAE family')
    if z.ndim!=5 or z.shape[1]!=16:raise ValueError('Expected Wan A14B16-channel latent')
    mean=torch.as_tensor(config.latents_mean,device=z.device,dtype=torch.float32).view(1,16,1,1,1)
    std=torch.as_tensor(config.latents_std,device=z.device,dtype=torch.float32).view(1,16,1,1,1)
    return z.float()*std+mean

def registered_messages(directory,shape):
    paths=sorted(Path(directory).glob('*.bin'))
    if len(paths)<2:raise ValueError('VideoMark requires a frozen multi-message registry')
    messages=[]
    for path in paths:
        raw=path.read_bytes()
        if len(raw)!=64:raise ValueError(f'Expected512information bits: {path.name}')
        messages.append(np.unpackbits(np.frombuffer(raw,dtype=np.uint8)).reshape(shape[1:]))
    if len({m.tobytes() for m in messages})!=len(messages):raise ValueError('Duplicate registry entries')
    return messages

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['videoshield','videomark','sigmark'],required=True)
    p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],default='hunyuan')
    for name in ['upstream','model-dir','case','message','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest',type=Path,default=Path('configs/sigmark_source_manifest.json'))
    p.add_argument('--registry',type=Path)
    p.add_argument('--memory-gib',type=float,default=12)
    a=p.parse_args();os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    start=time.monotonic();receipt=dict(status='starting',scope='Native baseline generation only; extraction pending',method=a.method,family=a.family,mode=a.mode)
    def save():
        receipt['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(receipt,indent=2));temp.replace(a.output/'receipt.json')
    try:
        torch.set_num_threads(4)
        case_bytes = a.case.read_bytes()
        case=json.loads(case_bytes);seed=int(case['seed'])
        raw=a.message.read_bytes()
        if len(raw)!=64:raise ValueError('Expected64byte information message')
        manifest=json.loads(a.manifest.read_text());cls=load_class(a.method,a.upstream,manifest)
        receipt.update(upstream_commit=manifest['commit'],case_sha256=hashlib.sha256(case_bytes).hexdigest(),seed=seed,information_bits=512,settings=dict(frames=65,size=[512,512],steps=50,cfg=6 if a.family=='hunyuan' else 5,shift=7 if a.family=='hunyuan' else 5,scheduler='FlowMatchEuler' if a.family=='hunyuan' else 'UniPC-flow',fps=8,crf=18,vae='float32',generator='bfloat16'),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        torch.manual_seed(seed);np.random.seed(seed)
        wm=cls(video_h=512,video_w=512,video_f=65,latent_c=16,vae_scale_factor_spatial=8,vae_scale_factor_temporal=4,ch_factor=2,hw_factor=8,fr_factor=16,batch_size=1,seed=seed,dtype=torch.float32,device='cpu')
        shape=wm.get_watermark_message_shape()
        if int(np.prod(shape))!=512:raise ValueError('Unexpected native message geometry')
        message=np.unpackbits(np.frombuffer(raw,dtype=np.uint8)).reshape(shape)
        initial=wm.create_watermarked_latents(message)
        if a.method=='videomark':
            if a.registry is None:raise ValueError('--registry required for VideoMark')
            catalog=registered_messages(a.registry,shape)
            if not any(np.array_equal(m,message[0]) for m in catalog):raise ValueError('Message absent from frozen registry')
            wm.maintained_info['watermark_messages']=catalog
            wm.maintained_info['encoding_key']=wm.encoding_key;wm.maintained_info['decoding_key']=wm.decoding_key
            receipt['registration_candidates']=len(catalog)
            receipt['registry_sha256']=hashlib.sha256(b''.join(m.tobytes() for m in catalog)).hexdigest()
        wm.save_maintained_info(str(a.output/'maintained_private.pkl'))
        receipt['state_sha256'] = hashlib.sha256((a.output/'maintained_private.pkl').read_bytes()).hexdigest()
        receipt['message_sha256'] = hashlib.sha256(raw).hexdigest()
        torch.save(initial,a.output/'initial_private.pt')
        (a.output/'message.bin').write_bytes(raw)
        receipt['status']='loading_model';save()
        from diffusers import HunyuanVideoPipeline,HunyuanVideoImageToVideoPipeline,AutoencoderKLHunyuanVideo,FlowMatchEulerDiscreteScheduler,WanPipeline,WanImageToVideoPipeline,AutoencoderKLWan,UniPCMultistepScheduler
        from PIL import Image
        torch.cuda.set_per_process_memory_fraction(a.memory_gib*1024**3/torch.cuda.get_device_properties(0).total_memory)
        vae_cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=vae_cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True);vae.enable_tiling()
        pipeline_cls=(HunyuanVideoImageToVideoPipeline if a.mode=='i2v' else HunyuanVideoPipeline) if a.family=='hunyuan' else (WanImageToVideoPipeline if a.mode=='i2v' else WanPipeline)
        pipe=pipeline_cls.from_pretrained(a.model_dir,vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        if a.family=='hunyuan':pipe.scheduler=FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config,shift=7)
        else:pipe.scheduler=UniPCMultistepScheduler.from_config(pipe.scheduler.config,flow_shift=5,use_flow_sigmas=True,prediction_type='flow_prediction')
        pipe.enable_sequential_cpu_offload(device='cuda:0')
        def callback(pipeline,step,timestep,kw):receipt.update(status='generating',step=int(step));save();return kw
        kwargs=dict(prompt=[case['prompt']],height=512,width=512,num_frames=65,num_inference_steps=50,guidance_scale=receipt['settings']['cfg'],latents=initial.to('cuda',torch.bfloat16),output_type='latent',return_dict=False,callback_on_step_end=callback)
        if a.mode=='i2v':
            image_bytes = Path(case['image']).read_bytes()
            receipt['conditioning_image_sha256'] = hashlib.sha256(image_bytes).hexdigest()
            with Image.open(BytesIO(image_bytes)) as image:
                kwargs['image'] = image.convert('RGB').resize((512,512))
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            z=pipe(**kwargs)[0].float();pipe.remove_all_hooks()
            for name in ['transformer','transformer_2','text_encoder','text_encoder_2','image_encoder']:
                module=getattr(pipe,name,None)
                if module is not None:module.to('cpu');setattr(pipe,name,None)
            pipe.vae.to('cuda');torch.cuda.empty_cache();receipt['status']='decoding';save()
            decoded_latent=denormalize_endpoint(z,pipe.vae.config,a.family)
            pixels=pipe.vae.decode(decoded_latent,return_dict=False)[0]
            frames=pipe.video_processor.postprocess_video(pixels,output_type='pil')[0]
            receipt['codec_command']=export_mp4(frames,a.output/'marked.mp4',crf=18)
        reread=load_mp4(a.output/'marked.mp4')
        if len(reread)!=65 or any(frame.size!=(512,512) for frame in reread):raise ValueError('Exported video geometry differs')
        receipt.update(status='completed_generation_only',video_sha256=hashlib.sha256((a.output/'marked.mp4').read_bytes()).hexdigest(),peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3)
    except Exception:
        receipt.update(status='failed',error=traceback.format_exc());raise
    finally:save()

if __name__=='__main__':main()
