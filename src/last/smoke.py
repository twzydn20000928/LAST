"""Fresh end-to-end LAST integration check. Never substitutes for the400-video benchmark."""
import argparse,json,time,os,hashlib,secrets,traceback
from pathlib import Path
import numpy as np
import torch
from .coding import BCH512
from .carriers import codebook
from .elmc import embed,feature
from .ccta import align
from .temporal import segments,windows
from .video import export_mp4,load_mp4

def main():
    p=argparse.ArgumentParser();p.add_argument('--family',choices=['hunyuan','wan22'],required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--memory-gib',type=float,default=12);p.add_argument('--offload',choices=['model','sequential'],default='sequential');a=p.parse_args()
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True);out=a.output/'receipt.json'
    if out.exists() and json.loads(out.read_text()).get('status')=='completed':return
    start=time.time();r={'status':'starting','scope':'fresh end-to-end smoke, not benchmark','family':a.family,'mode':a.mode,'rows':[],'settings':{'steps':50,'cfg':6 if a.family=='hunyuan' else 5,'shift':7 if a.family=='hunyuan' else 5,'frames':65,'size':[512,512],'clean_crf':18,'fps':8,'vae':'float32','generator':'bfloat16'},'hardware':'L40 (authorized A800 substitution)','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    def save():
        r['seconds']=time.time()-start;r['peak_allocated_gib']=torch.cuda.max_memory_allocated()/1024**3;temp=out.with_suffix('.tmp');temp.write_text(json.dumps(r,indent=2));temp.replace(out)
    try:
        from diffusers import HunyuanVideoPipeline,HunyuanVideoImageToVideoPipeline,WanPipeline,WanImageToVideoPipeline,AutoencoderKLHunyuanVideo,AutoencoderKLWan,FlowMatchEulerDiscreteScheduler,UniPCMultistepScheduler
        from PIL import Image
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(a.memory_gib*1024**3/torch.cuda.get_device_properties(0).total_memory)
        case=json.loads(a.case.read_text());seed=int(case['seed']);r['seed']=seed;r['case_sha256']=hashlib.sha256(a.case.read_bytes()).hexdigest();save()
        keyfile=a.output/'secret.key'
        if not keyfile.exists():keyfile.write_bytes(secrets.token_bytes(32));keyfile.chmod(0o600)
        private=a.output/'codes.pt'
        if not private.exists():torch.save(torch.from_numpy(codebook(keyfile.read_bytes())),private)
        codes=torch.load(private,weights_only=True);r['codebook_sha256']=hashlib.sha256(private.read_bytes()).hexdigest()
        msgfile=a.output/'message.npy'
        if not msgfile.exists():np.save(msgfile,np.unpackbits(np.frombuffer(secrets.token_bytes(64),dtype=np.uint8)))
        bits=np.load(msgfile);codec=BCH512();signs=codec.encode(bits).astype(np.float32)*2-1
        cls=(HunyuanVideoImageToVideoPipeline if a.mode=='i2v' else HunyuanVideoPipeline) if a.family=='hunyuan' else (WanImageToVideoPipeline if a.mode=='i2v' else WanPipeline)
        vae_cls=AutoencoderKLHunyuanVideo if a.family=='hunyuan' else AutoencoderKLWan
        vae=vae_cls.from_pretrained(a.model_dir,subfolder='vae',torch_dtype=torch.float32,local_files_only=True);vae.enable_tiling()
        pipe=cls.from_pretrained(a.model_dir,vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,low_cpu_mem_usage=True)
        if a.family=='hunyuan':pipe.scheduler=FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config,shift=7)
        else:pipe.scheduler=UniPCMultistepScheduler.from_config(pipe.scheduler.config,flow_shift=5,use_flow_sigmas=True,prediction_type='flow_prediction')
        if a.offload=='sequential':pipe.enable_sequential_cpu_offload(device='cuda:0')
        else:pipe.enable_model_cpu_offload()
        def callback(pipeline,step,timestep,kw):r.update(status='generating',step=int(step));save();return kw
        kwargs=dict(prompt=[case['prompt']],height=512,width=512,num_frames=65,num_inference_steps=50,guidance_scale=r['settings']['cfg'],latents=torch.randn(1,16,17,64,64,generator=torch.Generator().manual_seed(seed),dtype=torch.bfloat16).cuda(),output_type='latent',return_dict=False,callback_on_step_end=callback)
        if a.mode=='i2v':kwargs['image']=Image.open(case['image']).convert('RGB').resize((512,512))
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            z=pipe(**kwargs)[0].float();assert z.shape==(1,16,17,64,64)
            pipe.remove_all_hooks()
            for name in ['transformer','transformer_2','text_encoder','text_encoder_2','image_encoder']:
                module=getattr(pipe,name,None)
                if module is not None:module.to('cpu');setattr(pipe,name,None)
            pipe.vae.to('cuda');torch.cuda.empty_cache()
            def denorm(latent):
                if a.family=='hunyuan':return latent/pipe.vae.config.scaling_factor
                mean=torch.tensor(pipe.vae.config.latents_mean,device='cuda').view(1,16,1,1,1);std=torch.tensor(pipe.vae.config.latents_std,device='cuda').view(1,16,1,1,1);return latent*std+mean
            def norm(latent):
                if a.family=='hunyuan':return latent*pipe.vae.config.scaling_factor
                mean=torch.tensor(pipe.vae.config.latents_mean,device='cuda').view(1,16,1,1,1);std=torch.tensor(pipe.vae.config.latents_std,device='cuda').view(1,16,1,1,1);return (latent-mean)/std
            r['status']='embedding';save();marked=embed(z,codes,signs)
            for label,latent in [('reference',z),('marked',marked)]:
                pixels=pipe.vae.decode(denorm(latent).float(),return_dict=False)[0];frames=pipe.video_processor.postprocess_video(pixels,output_type='pil')[0]
                command=export_mp4(frames,a.output/f'{label}.mp4');r[label+'_codec_command']=command
                del pixels,frames
            del z,marked;torch.cuda.empty_cache();r['status']='reading';save()
            frames=load_mp4(a.output/'marked.mp4');nodes=list(windows(segments(frames)));features=[]
            for n in nodes:
                selected_frames=[frames[n['indices'][0]]]+[frames[i] for i in n['indices']]
                x=pipe.video_processor.preprocess_video([selected_frames]).to('cuda',torch.float32)
                latent=norm(pipe.vae.encode(x).latent_dist.mode());features.append(feature(latent).cpu())
            soft,meta=align(torch.stack(features) if features else torch.empty(0,1776),nodes,codes)
            predicted,dec=codec.decode(soft.cpu().numpy());np.save(a.output/'prediction.npy',predicted)
            r['rows']=[{'condition':'clean','correct_bits':int((predicted==bits).sum()),'total_bits':512,'exact_message':bool(np.array_equal(predicted,bits)),**dec,**meta}]
            r['marked_sha256']=hashlib.sha256((a.output/'marked.mp4').read_bytes()).hexdigest();r['status']='completed';save()
    except BaseException:r.update(status='failed',error=traceback.format_exc());save();raise

if __name__=='__main__':main()
