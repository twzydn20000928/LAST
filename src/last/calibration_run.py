"""Execute the frozen development grid with public generation and fidelity CLIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from .lfg_calibration import make_plan


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())


def validate_plan(plan, development, primary):
    first=plan['runs'][0]
    expected=make_plan(development,primary,first['method'],first['family'])
    for name in ('runs','fidelity_target','selection','samples_per_candidate','candidates'):
        if plan[name]!=expected[name]: raise ValueError('Calibration protocol changed: '+name)


def conditioning_case(sample, manifest, conditioning):
    first=manifest['samples'][(sample['index']//4)*4]
    folder=Path(conditioning)/f"prompt-{sample['index']//4:02}"
    if not (folder/'receipt.json').exists(): return None
    receipt=read(folder/'receipt.json')
    if receipt.get('status')!='completed': return None
    if receipt.get('prompt')!=first['prompt'] or receipt.get('seed')!=first['seed']:
        raise ValueError('Conditioning prompt or seed changed')
    if receipt.get('image_sha256')!=sha(folder/'input.png'):
        raise ValueError('Conditioning image changed')
    return dict(prompt=sample['prompt'],seed=sample['seed'],image=str((folder/'input.png').resolve()),
                video_id=sample['id'],key_slot=sample['key_slot'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','development','primary','root','state','conditioning','model-dir','writer-root'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--writer-python',type=Path,default=Path(sys.executable))
    p.add_argument('--max-jobs',type=int,default=1)
    p.add_argument('--memory-gib',type=float,default=8)
    p.add_argument('--min-free-mib',type=int,default=32000)
    a=p.parse_args()
    if a.max_jobs<1 or a.memory_gib<=0 or a.min_free_mib<(a.memory_gib+4)*1024:p.error('Invalid resource or job bound')
    import fcntl
    os.umask(0o077)
    plan,dev,primary=read(a.plan),read(a.development),read(a.primary)
    validate_plan(plan,dev,primary)
    for name,path in [('development',a.development),('primary',a.primary)]:
        if sha(path)!=plan['manifest_sha256'][name]:raise ValueError('Manifest checksum mismatch')
    writer=a.writer_root.resolve(); writer_hash=sha(writer/'src/last/smoke.py')
    if read(a.state/'state.json')['manifest_sha256']!=sha(a.development):raise ValueError('Development private state mismatch')
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['PYTHONPATH']=str(writer/'src')+os.pathsep+env.get('PYTHONPATH','')
    env['PYTHONNOUSERSITE']='1'
    jobs=0;missing=0
    for item in plan['runs']:
        folder=(root/item['run']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Unsafe output path')
        sample=dev['samples'][item['index']]
        case=conditioning_case(sample,dev,a.conditioning)
        if case is None:missing+=1;continue
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/'calibration.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:continue
            quality=folder/'quality.json';generation=folder/'receipt.json'
            target = folder / 'calibration.json'
            if target.exists():
                prior = read(target)
                if prior.get('status') != 'completed' or prior.get('item') != item:
                    raise ValueError(f'Unfinished or mismatched calibration run: {folder}')
                if not quality.is_file():
                    raise ValueError(f'Completed calibration run is missing its quality result: {folder}')
            if quality.exists():
                g=read(generation);q=read(quality)
                if g.get('status')!='completed' or g.get('source_sha256')!=writer_hash:
                    raise ValueError('Completed cell has another writer or unfinished generation')
                for key in ('family','mode','method','seed','lfg_alpha','lfg_final_steps'):
                    if g.get(key)!=item[key]:raise ValueError('Completed cell parameters changed')
                if sha(folder/'case.json')!=g.get('case_sha256'):raise ValueError('Completed case changed')
                saved=read(folder/'case.json')
                if any(saved.get(k)!=case[k] for k in ('prompt','seed','image')):raise ValueError('Completed conditioning changed')
                for name in ('reference','marked'):
                    if sha(folder/(name+'.mp4'))!=q.get(name+'_sha256'):raise ValueError('Completed quality video changed')
                if g['marked_sha256']!=q['marked_sha256']:raise ValueError('Completed generation/quality mismatch')
                continue
            if generation.exists():raise ValueError('Unfinished prior cell: inspect its process and retained failure before retry')
            free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
            if free<a.min_free_mib:
                print(json.dumps(dict(status='waiting_memory',free_mib=free,next=item['run'])));return
            path=folder/'case.json'
            if path.exists() and read(path)!=case:raise ValueError('Preexisting case differs')
            path.write_text(json.dumps(case,indent=2))
            key=a.state/'keys'/f"{sample['key_slot']:02}.key";message=a.state/'messages'/(sample['id']+'.bin')
            fingerprints={str(x):sha(x) for x in (key,message,path,a.plan,a.development,a.primary)}
            command=[str(a.writer_python),'-m','last.smoke','--method',item['method'],'--family',item['family'],'--mode','i2v',
                     '--model-dir',str(a.model_dir.resolve()),'--case',str(path),'--output',str(folder),
                     '--key',str(key.resolve()),'--message',str(message.resolve()),'--lfg-alpha',str(item['lfg_alpha']),
                     '--lfg-final-steps',str(item['lfg_final_steps']),'--memory-gib',str(a.memory_gib)]
            quality_command=[str(a.writer_python),'-m','last.quality','--reference',str(folder/'reference.mp4'),
                             '--marked',str(folder/'marked.mp4'),'--output',str(quality)]
            receipt=dict(status='running',item=item,plan_sha256=sha(a.plan),writer_source_sha256=writer_hash,
                         runner_sha256=sha(__file__),commands=[],started=time.time())
            def save():
                tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,indent=2));tmp.replace(target)
            save()
            try:
                for cmd in (command,quality_command):
                    with (folder/'calibration.log').open('ab') as log:
                        child=subprocess.Popen(cmd,cwd=writer,env=env,stdout=log,stderr=subprocess.STDOUT)
                        receipt['child_pid']=child.pid;save();rc=child.wait()
                    receipt['commands'].append(dict(argv=cmd,returncode=rc));save()
                    if rc:raise RuntimeError('Calibration command failed; no automatic retry')
                if any(sha(Path(x))!=h for x,h in fingerprints.items()) or sha(writer/'src/last/smoke.py')!=writer_hash:
                    raise ValueError('Inputs or writer changed during calibration')
                receipt['status']='completed';save();jobs+=1
            except BaseException:
                receipt['status']='failed';save();raise
            if jobs>=a.max_jobs:break
    print(json.dumps(dict(status='bounded_pass_finished',completed_this_pass=jobs,unavailable_conditioning=missing,
                          calibrated=False,selection_command='last.lfg_calibration_report')))


if __name__=='__main__':main()
