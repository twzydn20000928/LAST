"""Frozen native-baseline primary plan and bounded public-CLI execution.

This covers video generation and seven attacks, not V-score or exclusive timing.
Failed or interrupted jobs require inspection; they are never silently retried.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from .campaign import source_digest,digest
from .data import validate
from .report import aggregate

METHODS=('sigmark','videoshield','videomark')


def make_plan(manifest,manifest_sha):
    validate(manifest)
    runs=[dict(family=f,mode=m,method=w,video_id=r['id'],index=r['index'],key_slot=r['key_slot'],
               run=f"{f}/{m}/{w}/{r['id']}")
          for f in ('hunyuan','wan22') for m in ('i2v','t2v') for w in METHODS for r in manifest['samples']]
    return dict(schema_version=1,scope='400 samples per native method/backbone/mode; generation and seven attacks; quality and timing separate',
                manifest_sha256=manifest_sha,source_sha256=source_digest(),runs=runs)


def validate_plan(plan,manifest,manifest_sha):
    expected=make_plan(manifest,manifest_sha)
    for name in ('schema_version','scope','manifest_sha256','source_sha256','runs'):
        if plan.get(name)!=expected[name]:raise ValueError('Native campaign plan or source changed: '+name)


def commands_for(item,case,folder,state,model,upstream,memory_gib):
    common=['--family',item['family'],'--mode',item['mode'],'--method',item['method'],
            '--model-dir',str(model),'--upstream',str(upstream),'--memory-gib',str(memory_gib)]
    generate=[sys.executable,'-m','last.baseline_generate',*common,'--case',str(case),
              '--message',str(state/'messages'/(item['video_id']+'.bin')),'--output',str(folder)]
    if item['method']=='videomark':generate+=['--registry',str(state/'messages')]
    evaluate=[sys.executable,'-m','last.baseline_evaluate','--run',str(folder),'--video-id',item['video_id'],
              '--model-dir',str(model),'--upstream',str(upstream),'--memory-gib',str(memory_gib)]
    return generate,evaluate


def run(a):
    import fcntl
    plan=json.loads(a.plan.read_text());manifest=json.loads(a.manifest.read_text())
    validate_plan(plan,manifest,digest(a.manifest));validate(manifest,a.image_root)
    if json.loads((a.state/'state.json').read_text())['manifest_sha256']!=plan['manifest_sha256']:
        raise ValueError('Private state manifest mismatch')
    models=json.loads(a.models.read_text());root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    jobs=root/'.native-jobs';jobs.mkdir(exist_ok=True)
    registry=sorted((a.state/'messages').glob('*.bin'))
    if {p.stem for p in registry}!={s['id'] for s in manifest['samples']}:
        raise ValueError('Require the complete frozen400-message registry')
    inputs={str(p.resolve()):digest(p) for p in [a.plan,a.manifest,a.models,a.state/'state.json',*registry]}
    completed=0
    for position,item in enumerate(plan['runs']):
        if position%a.shards!=a.shard:continue
        if any(getattr(a,k) and getattr(a,k)!=item[k] for k in ('family','mode','method')):continue
        folder=(root/item['run']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Unsafe native output path')
        name=item['run'].replace('/','__');receipt=jobs/(name+'.json')
        with (jobs/(name+'.lock')).open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:continue
            single=dict(scope=plan['scope'],runs=[item])
            if receipt.exists():
                prior=json.loads(receipt.read_text())
                if prior.get('input_sha256')!=inputs:raise ValueError('Native campaign inputs changed')
                if prior.get('status')!='completed':raise ValueError('Inspect retained failed/interrupted native job before retry')
                if not aggregate(single,root,True)['complete']:raise ValueError('Completed native job no longer verifies')
                continue
            if folder.exists():raise ValueError('Unowned native output exists; audit rather than overwrite')
            free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
            if free<a.min_free_mib:
                print(json.dumps(dict(status='waiting_resources',next=item['run'],free_mib=free)));return
            row=manifest['samples'][item['index']]
            case=jobs/(name+'.case.json')
            case.write_text(json.dumps(dict(prompt=row['prompt'],seed=row['seed'],image=str((a.image_root/row['image']).resolve()),video_id=row['id']),indent=2))
            folder.parent.mkdir(parents=True,exist_ok=True)
            model=models[item['family']+'_'+item['mode']]
            cmds=commands_for(item,case,folder,a.state.resolve(),model,a.upstream.resolve(),a.memory_gib)
            image=a.image_root/row['image']
            job=dict(status='running',item=item,input_sha256=inputs,case_sha256=digest(case),image_sha256=digest(image),commands=[],started=time.time())
            def save():
                temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(job,indent=2));temp.replace(receipt)
            save()
            try:
                for cmd in cmds:
                    with (jobs/(name+'.log')).open('ab') as log:
                        child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
                        job['child_pid']=child.pid;save();rc=child.wait()
                    job['commands'].append(dict(argv=cmd,returncode=rc));save()
                    if rc:raise RuntimeError('Native command failed; preserve logs and outputs')
                if any(digest(p)!=h for p,h in inputs.items()) or digest(case)!=job['case_sha256'] or digest(image)!=job['image_sha256'] or source_digest()!=plan['source_sha256']:
                    raise ValueError('Native inputs or source changed during execution')
                if not aggregate(single,root,True)['complete']:raise ValueError('Native seven-condition audit incomplete')
                job.update(status='completed',seconds=time.time()-job['started']);save();completed+=1
            except BaseException as exc:
                job.update(status='failed',error=str(exc),seconds=time.time()-job['started']);save();raise
            if completed>=a.max_jobs:return


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    create=sub.add_parser('plan')
    for name in ('manifest','output'):create.add_argument('--'+name,type=Path,required=True)
    worker=sub.add_parser('run')
    for name in ('plan','manifest','root','state','image-root','models','upstream'):worker.add_argument('--'+name,type=Path,required=True)
    worker.add_argument('--family',choices=['hunyuan','wan22']);worker.add_argument('--mode',choices=['i2v','t2v']);worker.add_argument('--method',choices=METHODS)
    worker.add_argument('--shards',type=int,default=1);worker.add_argument('--shard',type=int,default=0)
    worker.add_argument('--max-jobs',type=int,default=1);worker.add_argument('--memory-gib',type=float,default=8)
    worker.add_argument('--min-free-mib',type=int,default=32000)
    a=p.parse_args();os.umask(0o077)
    if a.command=='plan':
        result=make_plan(json.loads(a.manifest.read_text()),digest(a.manifest));a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        print(json.dumps(dict(runs=len(result['runs']),conditions=7*len(result['runs']))))
    else:
        if a.shards<1 or not 0<=a.shard<a.shards or a.max_jobs<1 or a.memory_gib<=0 or a.min_free_mib<(a.memory_gib+4)*1024:
            p.error('Invalid shard, job bound or memory gate')
        run(a)


if __name__=='__main__':main()

