"""Generate outcome-independent conditioning inputs for the development split."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
import torch
from .development import validate_development
from .video import export_mp4,load_mp4


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('configs/development_manifest.json'))
    p.add_argument('--primary',type=Path,default=Path('configs/primary_manifest.json'))
    p.add_argument('--prompt-index',type=int,choices=range(20),required=True)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--memory-gib',type=float,default=8);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());validate_development(manifest,json.loads(a.primary.read_text()))
    sample=manifest['samples'][a.prompt_index*4]
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    start=time.monotonic()
    record=dict(status='starting',scope='Development conditioning reconstruction; no watermark or outcome-based selection',
                sample_id=sample['id'],prompt=sample['prompt'],seed=sample['seed'],
                manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                model_family='hunyuan_t2v',expected_model_revision='e8c2aaa66fe3742a32c11a6766aecbf07c56e773',
                settings=dict(steps=50,cfg=6,shift=7,frames=65,size=[512,512],fps=8,crf=18,vae='float32',generator='bfloat16'),
                selection='First frame after actual MP4 reread; reuse this one image for all four seeds of this prompt')
    def save():
        record['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(a.output/'receipt.json')
    save()
    try:
        from diffusers import HunyuanVideoPipeline,AutoencoderKLHunyuanVideo,FlowMatchEulerDiscreteScheduler
        torch.set_num_threads(4)
        torch.cuda.set_per_process_memory_fraction(a.memory_gib*1024**3/torch.cuda.get_device_properties(0).total_memory)
        vae=AutoencoderKLHunyuanVideo.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True);vae.enable_tiling()
        pipe=HunyuanVideoPipeline.from_pretrained(a.model_dir,vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        pipe.scheduler=FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config,shift=7)
        pipe.enable_sequential_cpu_offload(device='cuda:0')
        def callback(pipeline,step,timestep,kw):record.update(status='generating',step=int(step));save();return kw
        seed=sample['seed'];torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        initial=torch.randn(1,16,17,64,64,generator=torch.Generator().manual_seed(seed),dtype=torch.bfloat16).cuda()
        with torch.inference_mode():
            z=pipe(prompt=[sample['prompt']],height=512,width=512,num_frames=65,num_inference_steps=50,
                   guidance_scale=6,latents=initial,output_type='latent',return_dict=False,callback_on_step_end=callback)[0].float()
            pipe.remove_all_hooks()
            for name in ('transformer','text_encoder','text_encoder_2'):
                module=getattr(pipe,name,None)
                if module is not None:module.to('cpu');setattr(pipe,name,None)
            pipe.vae.to('cuda');torch.cuda.empty_cache();record['status']='decoding';save()
            pixels=pipe.vae.decode(z/pipe.vae.config.scaling_factor,return_dict=False)[0]
            frames=pipe.video_processor.postprocess_video(pixels,output_type='pil')[0]
            record['codec_command']=export_mp4(frames,a.output/'reference.mp4')
        reread=load_mp4(a.output/'reference.mp4')
        if len(reread)!=65 or any(f.size!=(512,512) for f in reread):raise ValueError('Unexpected conditioning video geometry')
        reread[0].save(a.output/'input.png')
        record.update(status='completed',reference_sha256=hashlib.sha256((a.output/'reference.mp4').read_bytes()).hexdigest(),
                      image_sha256=hashlib.sha256((a.output/'input.png').read_bytes()).hexdigest(),
                      peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3)
        save()
    except BaseException:record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
