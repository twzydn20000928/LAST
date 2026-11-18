"""Plan and resume the LAST/LFG primary comparison using public entry points."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from .data import validate
from .report import CONDITIONS

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_job(receipt, job):
    # The caller holds the per-job lock. Readers may inspect this path concurrently.
    pending = receipt.with_suffix('.tmp')
    pending.write_text(json.dumps(job, indent=2))
    pending.replace(receipt)

def source_digest():
    h=hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        h.update(path.name.encode());h.update(path.read_bytes())
    return h.hexdigest()

def make_plan(manifest,manifest_sha):
    validate(manifest)
    runs=[]
    for family in ['hunyuan','wan22']:
        for mode in ['i2v','t2v']:
            for method in ['last','lfg']:
                for row in manifest['samples']:
                    runs.append(dict(family=family,mode=mode,method=method,video_id=row['id'],index=row['index'],key_slot=row['key_slot'],run=f"{family}/{mode}/{method}/{row['id']}"))
    return dict(schema_version=1,scope='Primary400samples per backbone/mode/method; LAST and LFG only, other baselines separate',manifest_sha256=manifest_sha,source_sha256=source_digest(),runs=runs)

def run_worker(a):
    import fcntl
    plan=json.loads(a.plan.read_text());manifest=json.loads(a.manifest.read_text());validate(manifest,a.image_root)
    if digest(a.manifest)!=plan['manifest_sha256']:raise ValueError('Manifest differs from frozen plan')
    if source_digest()!=plan['source_sha256']:raise ValueError('Scientific source differs from frozen plan; audit before creating a new campaign')
    state=json.loads((a.state/'state.json').read_text())
    if state['manifest_sha256']!=plan['manifest_sha256']:raise ValueError('Private state belongs to another manifest')
    models=json.loads(a.models.read_text())
    a.root.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','last.doctor','--strict','--output',str(a.root/f'environment-shard-{a.shard}.json')],check=True)
    completed=0
    for position,item in enumerate(plan['runs']):
        if position%a.shards!=a.shard:continue
        if a.family and item['family']!=a.family:continue
        if a.mode and item['mode']!=a.mode:continue
        if a.method and item['method']!=a.method:continue
        folder=(a.root/item['run']).resolve()
        if not folder.is_relative_to(a.root.resolve()):raise ValueError('Unsafe run path')
        folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (folder/'job.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:continue
            receipt=folder/'campaign.json'
            if receipt.exists():
                prior=json.loads(receipt.read_text())
                if prior['plan_sha256']!=digest(a.plan):raise ValueError('Existing run belongs to another plan')
                if prior.get('status')=='completed':
                    if not (folder/'quality.json').exists() or any(not (folder/'attacks'/(n+'.json')).exists() for n in CONDITIONS):raise ValueError('Completed run is missing artifacts')
                    continue
            free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
            if free<(a.memory_gib+4)*1024:
                print(json.dumps(dict(status='waiting_memory',free_mib=free,next=item['run'])),flush=True);return
            row=manifest['samples'][item['index']]
            if row['id']!=item['video_id'] or row['key_slot']!=item['key_slot']:raise ValueError('Plan/sample mismatch')
            case=folder/'case.json';case.write_text(json.dumps(dict(prompt=row['prompt'],seed=row['seed'],image=str((a.image_root/row['image']).resolve()),video_id=row['id'],key_slot=row['key_slot']),indent=2))
            model=models[item['family']+'_'+item['mode']]
            job=dict(status='running',item=item,manifest_sha256=plan['manifest_sha256'],plan_sha256=digest(a.plan),commands=[],started=time.time())
            if receipt.exists():receipt.rename(folder/f'campaign.previous-{time.time_ns()}.json')
            commands=[
                [sys.executable,'-m','last.smoke','--family',item['family'],'--mode',item['mode'],'--method',item['method'],'--model-dir',model,'--case',str(case),'--output',str(folder),'--key',str(a.state/'keys'/f"{row['key_slot']:02}.key"),'--message',str(a.state/'messages'/(row['id']+'.bin')),'--memory-gib',str(a.memory_gib),'--offload',a.offload],
                [sys.executable,'-m','last.evaluate','--family',item['family'],'--model-dir',model,'--run',str(folder),'--video-id',row['id']],
                [sys.executable,'-m','last.quality','--reference',str(folder/'reference.mp4'),'--marked',str(folder/'marked.mp4'),'--output',str(folder/'quality.json')],
            ]
            try:
                for command in commands:
                    save_job(receipt,job)
                    with (folder/'job.log').open('ab') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
                    job['commands'].append(dict(argv=command,returncode=result.returncode))
                    if result.returncode:raise RuntimeError(f'Command failed:{command[2]}')
                for name in CONDITIONS:
                    r=json.loads((folder/'attacks'/(name+'.json')).read_text())
                    if r['status']!='completed':raise RuntimeError(f'Incomplete attack:{name}')
                job['status']='completed';completed+=1
            except Exception as exc:job.update(status='failed',error=str(exc))
            job['seconds']=time.time()-job['started'];save_job(receipt,job);print(json.dumps(dict(run=item['run'],status=job['status'])),flush=True)
            if job['status']=='failed':raise SystemExit(1)
            if a.max_jobs and completed>=a.max_jobs:return

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    create=sub.add_parser('plan');create.add_argument('--manifest',type=Path,required=True);create.add_argument('--output',type=Path,required=True)
    worker=sub.add_parser('run')
    for name in ['plan','manifest','root','state','image-root','models']:worker.add_argument('--'+name,type=Path,required=True)
    worker.add_argument('--family',choices=['hunyuan','wan22']);worker.add_argument('--mode',choices=['i2v','t2v']);worker.add_argument('--method',choices=['last','lfg'])
    worker.add_argument('--shards',type=int,default=1);worker.add_argument('--shard',type=int,default=0);worker.add_argument('--max-jobs',type=int,default=0);worker.add_argument('--memory-gib',type=float,default=12);worker.add_argument('--offload',choices=['model','sequential'],default='sequential')
    a=p.parse_args();os.umask(0o077)
    if a.command=='plan':
        plan=make_plan(json.loads(a.manifest.read_text()),digest(a.manifest));a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as f:json.dump(plan,f,indent=2)
        print(json.dumps(dict(runs=len(plan['runs']),conditions=7*len(plan['runs']))))
    else:
        if a.shards<1 or not 0<=a.shard<a.shards or a.max_jobs<0:raise ValueError('Invalid shard or job limit')
        run_worker(a)
if __name__=='__main__':main()
