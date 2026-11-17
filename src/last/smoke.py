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
    p=argparse.ArgumentParser();p.add_argument('--family',choices=['hunyuan','wan22'],required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--memory-gib',type=float,default=12);p.add_argument('--offload',choices=['model','sequential'],default='sequential');p.add_argument('--key',type=Path);p.add_argument('--message',type=Path);p.add_argument('--method',choices=['last','lfg','lfg-c'],default='last')
    p.add_argument('--mu',type=float,default=.5);p.add_argument('--fixed-target',action='store_true')
    p.add_argument('--uniform-profile',action='store_true',help='Supplement control: all sixteen message groups use mu; main default remains non-uniform')
    p.add_argument('--lfg-alpha',type=float,default=.15)
    p.add_argument('--lfg-final-steps',type=int,choices=[5,10,20],default=10)
    a=p.parse_args()
    if not np.isfinite(a.mu) or a.mu<0:p.error('--mu must be finite and nonnegative')
    if a.method!='last' and (a.mu!=.5 or a.fixed_target or a.uniform_profile):p.error('Margin options apply only to LAST')
    if not np.isfinite(a.lfg_alpha) or a.lfg_alpha<0:p.error('--lfg-alpha must be finite and nonnegative')
    if a.method not in ('lfg','lfg-c') and (a.lfg_alpha!=.15 or a.lfg_final_steps!=10):p.error('LFG options apply only to LFG')
    if bool(a.key)!=bool(a.message):p.error('--key and --message must be supplied together')
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True);out=a.output/'receipt.json'
    if out.exists() and json.loads(out.read_text()).get('status')=='completed':
        prior=json.loads(out.read_text())
        if prior.get('mu',.5)!=a.mu or prior.get('fixed_target',False)!=a.fixed_target:raise ValueError('Completed run has another embedding configuration')
        if prior.get('uniform_profile',False)!=a.uniform_profile:raise ValueError('Completed run has another group margin profile')
        if prior.get('method','last')!=a.method:raise ValueError('Completed output belongs to a different method')
        if prior.get('lfg_alpha',.15)!=a.lfg_alpha or prior.get('lfg_final_steps',10)!=a.lfg_final_steps:raise ValueError('Completed output has another LFG configuration')
        if prior['family']!=a.family or prior['mode']!=a.mode or prior['case_sha256']!=hashlib.sha256(a.case.read_bytes()).hexdigest():raise ValueError('Completed output belongs to a different case/configuration')
        if a.key and (a.output/'secret.key').read_bytes()!=a.key.read_bytes():raise ValueError('Completed output belongs to a different key')
        if a.message and not np.array_equal(np.load(a.output/'message.npy'),np.unpackbits(np.frombuffer(a.message.read_bytes(),dtype=np.uint8))):raise ValueError('Completed output belongs to a different message')
        return
    start=time.time();r={'status':'starting','scope':'fresh end-to-end smoke, not benchmark','family':a.family,'mode':a.mode,'rows':[],'settings':{'steps':50,'cfg':6 if a.family=='hunyuan' else 5,'shift':7 if a.family=='hunyuan' else 5,'frames':65,'size':[512,512],'clean_crf':18,'fps':8,'vae':'float32','generator':'bfloat16'},'hardware':'L40 (authorized A800 substitution)','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    def save():
        r['seconds']=time.time()-start;r['peak_allocated_gib']=torch.cuda.max_memory_allocated()/1024**3;temp=out.with_suffix('.tmp');temp.write_text(json.dumps(r,indent=2));temp.replace(out)
    try:
        r['offload']=a.offload;r['memory_limit_gib']=a.memory_gib;r['model_directory']=str(a.model_dir);r['method']=a.method;r['mu']=a.mu;r['fixed_target']=a.fixed_target
        r['lfg_alpha']=a.lfg_alpha;r['lfg_final_steps']=a.lfg_final_steps
        r['uniform_profile']=a.uniform_profile
        from diffusers import HunyuanVideoPipeline,HunyuanVideoImageToVideoPipeline,WanPipeline,WanImageToVideoPipeline,AutoencoderKLHunyuanVideo,AutoencoderKLWan,FlowMatchEulerDiscreteScheduler,UniPCMultistepScheduler
        from PIL import Image
        torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(a.memory_gib*1024**3/torch.cuda.get_device_properties(0).total_memory)
        case=json.loads(a.case.read_text());seed=int(case['seed']);r['seed']=seed;r['case_sha256']=hashlib.sha256(a.case.read_bytes()).hexdigest();save()
        keyfile=a.output/'secret.key'
        if a.key:
            supplied=a.key.read_bytes()
            if len(supplied)!=32:raise ValueError('Expected32byte key')
            if keyfile.exists() and keyfile.read_bytes()!=supplied:raise ValueError('Existing run has a different key')
            if not keyfile.exists():keyfile.write_bytes(supplied)
        if not keyfile.exists():keyfile.write_bytes(secrets.token_bytes(32));keyfile.chmod(0o600)
        private=a.output/'codes.pt'
        if not private.exists():torch.save(torch.from_numpy(codebook(keyfile.read_bytes())),private)
        codes=torch.load(private,weights_only=True);r['codebook_sha256']=hashlib.sha256(private.read_bytes()).hexdigest()
        msgfile=a.output/'message.npy'
        if a.message:
            supplied=a.message.read_bytes()
            if len(supplied)!=64:raise ValueError('Expected64byte512bit message')
            supplied_bits=np.unpackbits(np.frombuffer(supplied,dtype=np.uint8))
            if msgfile.exists() and not np.array_equal(np.load(msgfile),supplied_bits):raise ValueError('Existing run has a different message')
            if not msgfile.exists():np.save(msgfile,supplied_bits)
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
            if a.method in ('lfg','lfg-c'):
                from .lfg import watermark
                from .lfg_schedulers import LFGFlowEuler,LFGUniPC
                scheduler_cls=LFGFlowEuler if a.family=='hunyuan' else LFGUniPC
                pipe.scheduler=scheduler_cls.from_config(pipe.scheduler.config)
                pipe.scheduler.alpha=a.lfg_alpha;pipe.scheduler.late_steps=a.lfg_final_steps
                if a.method=='lfg-c':
                    from .lfg_c import watermark as shared_watermark,perturbation as shared_perturbation
                    pipe.scheduler.spread=shared_watermark(codes,signs).cuda()
                    pipe.scheduler.carrier_perturbation=shared_perturbation
                    r['controlled_adaptation']='Shared DCT carrier; per-group coefficient standard deviation; no margin projection'
                else:pipe.scheduler.spread=watermark(keyfile.read_bytes(),signs).cuda()
                torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
                r['generation_branch']=a.method;save()
                marked=pipe(**kwargs)[0].float()
                pipe.scheduler.spread=None
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
            r['status']='embedding';save()
            if a.method=='last':marked=embed(z,codes,signs,mu=a.mu,fixed_target=a.fixed_target,uniform=a.uniform_profile)
            for label,latent in [('reference',z),('marked',marked)]:
                pixels=pipe.vae.decode(denorm(latent).float(),return_dict=False)[0];frames=pipe.video_processor.postprocess_video(pixels,output_type='pil')[0]
                command=export_mp4(frames,a.output/f'{label}.mp4');r[label+'_codec_command']=command
                del pixels,frames
            del z,marked;torch.cuda.empty_cache();r['status']='reading';save()
            frames=load_mp4(a.output/'marked.mp4')
            if a.method=='lfg':
                from .lfg import scores,align_received_frames
                x=pipe.video_processor.preprocess_video([align_received_frames(frames)]).to('cuda',torch.float32)
                latent=norm(pipe.vae.encode(x).latent_dist.mode())
                soft=scores(latent,keyfile.read_bytes());meta={'route':'lfg_received_order','groups':16}
            else:
                nodes=list(windows(segments(frames)));features=[]
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

