"""Generate the frozen80 LAST development videos without outcome selection."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from .campaign import source_digest
from .development import validate_development
from .development_case import build
from .feature_cache import sha


def make_plan(development, primary, family):
    validate_development(development, primary)
    if family not in ('hunyuan', 'wan22'):
        raise ValueError('Unknown family')
    return dict(schema_version=1, family=family, mode='i2v', method='last', mu=.5,
                fixed_target=False, uniform_profile=False,
                source_sha256=source_digest(),
                scope='All80 frozen development samples; unchanged LAST writer; no outcome selection',
                samples=[dict(id=r['id'], index=r['index'], key_slot=r['key_slot']) for r in development['samples']])


def validate_plan(plan, development, primary):
    if plan != make_plan(development, primary, plan['family']):
        raise ValueError('Development plan or source changed')


def run(a):
    import fcntl
    read=lambda p:json.loads(p.read_text())
    dev,primary,plan=read(a.development),read(a.primary),read(a.plan)
    validate_plan(plan,dev,primary)
    dev_sha=sha(a.development)
    if read(a.state/'state.json')['manifest_sha256']!=dev_sha:
        raise ValueError('Private state belongs to another development manifest')
    a.output.mkdir(parents=True,exist_ok=True)
    finished=0;missing=0
    for item in plan['samples']:
        conditioning=a.conditioning/f"prompt-{item['index']//4:02}"
        if not (conditioning/'receipt.json').exists() or read(conditioning/'receipt.json').get('status')!='completed':
            missing+=1;continue
        case=build(dev,item['id'],'i2v',dev_sha,conditioning)
        folder=a.output/item['id'];folder.mkdir(exist_ok=True)
        with (folder/'job.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:continue
            receipt=folder/'development.json'
            key=a.state/'keys'/f"{item['key_slot']:02}.key"
            message=a.state/'messages'/(item['id']+'.bin')
            if receipt.exists():
                old=read(receipt)
                if old['status']!='completed':raise ValueError('Prior unfinished job; inspect before retrying')
                if old['plan_sha256']!=sha(a.plan) or read(folder/'case.json')!=case:
                    raise ValueError('Completed development configuration changed')
                if any(sha(Path(p))!=h for p,h in old['input_sha256'].items()):
                    raise ValueError('Completed development inputs changed')
                if any(sha(folder/n)!=h for n,h in old['files_sha256'].items()):
                    raise ValueError('Completed development artifacts changed')
                continue
            if (folder/'receipt.json').exists():raise ValueError('Unregistered prior generation; audit before reuse')
            free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
            if free<a.min_free_mib:
                print(json.dumps(dict(status='waiting_resources',next=item['id'])));return
            if len(key.read_bytes())!=32 or len(message.read_bytes())!=64:raise ValueError('Invalid private inputs')
            casepath=folder/'case.json';casepath.write_text(json.dumps(case,indent=2))
            inputs={str(p.resolve()):sha(p) for p in (a.plan,a.development,a.primary,a.state/'state.json',key,message,casepath,conditioning/'input.png',conditioning/'receipt.json')}
            commands=[
                [sys.executable,'-m','last.smoke','--family',plan['family'],'--mode','i2v','--method','last','--mu','0.5','--model-dir',str(a.model_dir),'--case',str(casepath),'--output',str(folder),'--key',str(key),'--message',str(message),'--memory-gib',str(a.memory_gib),'--offload','sequential'],
                [sys.executable,'-m','last.quality','--reference',str(folder/'reference.mp4'),'--marked',str(folder/'marked.mp4'),'--output',str(folder/'quality.json')]]
            record=dict(status='running',plan_sha256=sha(a.plan),input_sha256=inputs,commands=[],started=time.time())
            def save():
                temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(record,indent=2));temp.replace(receipt)
            save()
            try:
                for command in commands:
                    with (folder/'development.log').open('ab') as log:
                        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                        record['child_pid']=child.pid;save();rc=child.wait()
                    record['commands'].append(dict(argv=command,returncode=rc));save()
                    if rc:raise RuntimeError('Development command failed; no automatic retry')
                if any(sha(Path(p))!=h for p,h in inputs.items()) or source_digest()!=plan['source_sha256']:
                    raise ValueError('Inputs or source changed during generation')
                g,q=read(folder/'receipt.json'),read(folder/'quality.json')
                if g['status']!='completed':raise ValueError('Generation incomplete')
                for name in ('marked','reference'):
                    if sha(folder/(name+'.mp4'))!=q[name+'_sha256']:raise ValueError('Quality/video mismatch')
                if g['marked_sha256']!=q['marked_sha256']:raise ValueError('Generation/video mismatch')
                record.update(status='completed',seconds=time.time()-record['started'],files_sha256={n:sha(folder/n) for n in ('case.json','receipt.json','quality.json','marked.mp4','reference.mp4','codes.pt','message.npy')})
                save();finished+=1
            except BaseException:
                record['status']='failed';save();raise
            if finished>=a.max_jobs:break
    print(json.dumps(dict(status='bounded_pass_finished',completed_this_pass=finished,missing_conditioning=missing,calibration_complete=False)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['plan','run'])
    for name in ('development','primary','plan'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],default='hunyuan')
    for name in ('state','conditioning','model-dir','output'):p.add_argument('--'+name,type=Path)
    p.add_argument('--max-jobs',type=int,default=1);p.add_argument('--memory-gib',type=float,default=8)
    p.add_argument('--min-free-mib',type=int,default=32000)
    a=p.parse_args();os.umask(0o077)
    if a.command=='plan':
        result=make_plan(json.loads(a.development.read_text()),json.loads(a.primary.read_text()),a.family)
        with a.plan.open('x') as f:json.dump(result,f,indent=2)
    else:
        if any(getattr(a,n) is None for n in ('state','conditioning','model_dir','output')):p.error('run requires state, conditioning, model-dir, output')
        if a.max_jobs<1 or a.memory_gib<=0 or a.min_free_mib<(a.memory_gib+4)*1024:p.error('Invalid resource bound')
        run(a)


if __name__=='__main__':main()
