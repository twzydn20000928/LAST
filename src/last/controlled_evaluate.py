"""Run shared-fusion readers on identical exported videos (Table12 controls)."""
import argparse,json,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from .campaign import digest,source_digest
from .reader_ablation import verified_attack,writer_method

READERS=('received','calibrated_energy','ccta','oracle')
CONDITIONS=('clean','drop','compression')


def commands(reader,video,attack,codes,model,family,cache,output,calibration):
    if reader not in READERS:raise ValueError('Unknown reader')
    if reader=='calibrated_energy' and calibration is None:raise ValueError('Full80 frozen calibration required')
    kind='oracle' if reader=='oracle' else ('received' if reader=='received' else 'ccta')
    module='last.oracle_feature_cache' if kind=='oracle' else 'last.feature_cache'
    acquire=[sys.executable,'-m',module,'--family',family,'--model-dir',str(model),'--video',str(video),'--output',str(cache)]
    if kind=='oracle':acquire+=['--attack-receipt',str(attack)]
    else:acquire+=['--reader',kind]
    extract=[sys.executable,'-m','last.controlled_extract','--reader',reader,'--video',str(video),
             '--cache',str(cache),'--codes',str(codes),'--output',str(output)]
    if reader=='calibrated_energy':extract+=['--calibration',str(calibration)]
    return acquire,extract


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True)
    p.add_argument('--calibration',type=Path)
    p.add_argument('--readers',nargs='+',choices=READERS,default=list(READERS))
    a=p.parse_args();os.umask(0o077)
    if len(set(a.readers))!=len(a.readers):p.error('Duplicate reader')
    if 'calibrated_energy' in a.readers and not a.calibration:p.error('Full comparison requires --calibration')
    generation=json.loads((a.run/'receipt.json').read_text());method=writer_method(generation,a.family)
    attacks={name:verified_attack(a.run,name,generation) for name in CONDITIONS}
    model_files=sorted(f for f in (a.model_dir/'vae').iterdir() if f.is_file() and f.suffix in ('.json','.safetensors','.bin'))
    if not model_files:raise ValueError('Missing VAE model files')
    paths=[a.run/'receipt.json',a.run/'codes.pt',a.run/'message.npy',a.run/'marked.mp4',*model_files]
    for condition,(_,video) in attacks.items():paths.extend([video,a.run/'attacks'/(condition+'.json')])
    if a.calibration:paths.append(a.calibration)
    fingerprints={str(f.resolve()):digest(f) for f in paths};sources=source_digest()
    # New output per invocation. No partially successful retry is silently reused.
    a.output.mkdir(parents=True,exist_ok=False)
    record=dict(status='running',writer=method,family=a.family,readers=a.readers,conditions=list(CONDITIONS),
                complete_reader_set=set(a.readers)==set(READERS),input_sha256=fingerprints,source_sha256=sources,
                scope='One writer case, same exported clean/drop/compression inputs; not full400 aggregate',steps=[],rows=[])
    start=time.monotonic()
    def save():
        record['seconds']=time.monotonic()-start
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(a.output/'receipt.json')
    def unchanged():
        if source_digest()!=sources or any(digest(Path(f))!=h for f,h in fingerprints.items()):raise ValueError('Inputs or scientific source changed')
    def execute(command,name):
        with (a.output/(name+'.log')).open('w') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            record['child_pid']=child.pid;save();rc=child.wait()
        record['steps'].append(dict(command=command,returncode=rc));save()
        if rc:raise RuntimeError(name+' failed; preserve output and inspect before retry')
    save()
    try:
        for condition,(_,video) in attacks.items():
            caches=set()
            for reader in a.readers:
                unchanged()
                kind='oracle' if reader=='oracle' else ('received' if reader=='received' else 'ccta')
                cache=a.output/(condition+'-'+kind+'-features');output=a.output/(condition+'-'+reader+'-read')
                acquire,extract=commands(reader,video,a.run/'attacks'/(condition+'.json'),a.run/'codes.pt',
                                         a.model_dir,a.family,cache,output,a.calibration)
                if kind not in caches:execute(acquire,condition+'-'+kind+'-acquire');caches.add(kind)
                execute(extract,condition+'-'+reader+'-extract')
                receipt=json.loads((output/'receipt.json').read_text());decoded=output/'decoded-private.json'
                if receipt['status']!='completed' or receipt['blind']!=(reader!='oracle') or receipt['decoded_sha256']!=digest(decoded):
                    raise ValueError('Incomplete or inconsistent controlled extraction')
                pred=np.asarray(json.loads(decoded.read_text())['information_bits'])
                # Truth is read only after this reader returned; never a child argument.
                truth=np.load(a.run/'message.npy',allow_pickle=False)
                if pred.shape!=truth.shape or pred.shape!=(512,) or not np.isin(pred,[0,1]).all() or not np.isin(truth,[0,1]).all():
                    raise ValueError('Expected512 binary information bits')
                unchanged()
                record['rows'].append(dict(condition=condition,reader=reader,blind=reader!='oracle',
                    correct_bits=int((pred==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(pred,truth)),
                    received_sha256=digest(video),feature_receipt_sha256=digest(cache/'receipt.json'),
                    extraction_receipt_sha256=digest(output/'receipt.json'),selection=receipt['selection']))
                save()
        record['status']='completed';save()
    except BaseException:
        record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
