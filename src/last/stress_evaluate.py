"""Evaluate exported stress videos using an isolated blind LAST extraction CLI."""
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from .campaign import digest,source_digest


def recount(prediction, truth, video_sha, family):
    if (prediction.get('video_sha256')!=video_sha or prediction.get('family')!=family
            or prediction.get('information_bits')!=512):
        raise ValueError('Decoded output identity mismatch')
    bits=np.unpackbits(np.frombuffer(bytes.fromhex(prediction['message_hex']),dtype=np.uint8))
    if bits.shape!=(512,) or truth.shape!=(512,) or not np.isin(truth,[0,1]).all():
        raise ValueError('Wrong information payload')
    return dict(correct_bits=int((bits==truth).sum()),total_bits=512,
                exact_message=bool(np.array_equal(bits,truth)))


def verify_counts(record, prediction, truth, attack, family):
    if any(record.get(k)!=attack[k] for k in ('attack','seed','video_id')):
        raise ValueError('Cached stress condition mismatch')
    measured=recount(prediction,truth,attack['received_sha256'],family)
    if any(record.get(k)!=v for k,v in measured.items()):
        raise ValueError('Cached stress counts disagree with saved prediction')


def verify_completed(record, inputs, sources, decoded):
    if (record.get('status')!='completed' or record.get('input_sha256')!=inputs
            or record.get('source_sha256_files')!=sources):
        raise ValueError('Cached stress evidence lacks matching input/source provenance; use a new output directory')
    if not decoded.is_file() or record.get('decoded_sha256')!=digest(decoded):
        raise ValueError('Cached stress prediction changed or is missing')

def verify_attack(folder,source_sha):
    row=json.loads((folder/'attack.json').read_text())
    if row.get('status')!='completed_attack_export' or row['source_sha256']!=source_sha:raise ValueError('Stress source mismatch or incomplete export')
    video=folder/'received.mp4'
    if hashlib.sha256(video.read_bytes()).hexdigest()!=row['received_sha256']:raise ValueError('Stress received video changed')
    return row,video

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['run','attacks','output','model-dir']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);a=p.parse_args()
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True,mode=0o700)
    source_sha=hashlib.sha256((a.run/'marked.mp4').read_bytes()).hexdigest()
    generation=json.loads((a.run/'receipt.json').read_text())
    if generation.get('status')!='completed' or generation.get('method')!='last' or generation['family']!=a.family:raise ValueError('Expected completed matching LAST generation')
    if generation.get('marked_sha256')!=source_sha:raise ValueError('Generation MP4 changed')
    model_files=sorted(f for f in (a.model_dir/'vae').iterdir() if f.is_file() and f.suffix in ('.json','.safetensors','.bin'))
    if not model_files:raise ValueError('Missing VAE model files')
    sources=source_digest()
    common=[a.run/'receipt.json',a.run/'marked.mp4',a.run/'secret.key',a.run/'message.npy',*model_files]
    folders=sorted(path.parent for path in a.attacks.glob('*/attack.json'))
    if not folders:raise ValueError('No exported stress conditions')
    failed=False
    for folder in folders:
        attack,video=verify_attack(folder,source_sha);out=a.output/folder.name;out.mkdir(exist_ok=True,mode=0o700)
        inputs={str(f.resolve()):digest(f) for f in [*common,folder/'attack.json',video]}
        receipt=out/'evaluation.json'
        decoded=out/'decoded_private.json'
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            if prior.get('received_sha256')!=attack['received_sha256']:raise ValueError('Existing evaluation belongs to another video')
            if prior.get('status')=='completed':
                verify_completed(prior,inputs,sources,decoded)
                verify_counts(prior,json.loads(decoded.read_text()),np.load(a.run/'message.npy',allow_pickle=False),attack,a.family)
                continue
            receipt.rename(out/f'evaluation.failed-{time.time_ns()}.json')
        # Preserve any unsuccessful prior extraction output; never silently reuse it.
        if decoded.exists():decoded.rename(out/f'decoded.previous-{time.time_ns()}.json')
        result=dict(status='running',attack=attack['attack'],seed=attack['seed'],video_id=attack['video_id'],source_sha256=source_sha,received_sha256=attack['received_sha256'],input_sha256=inputs,source_sha256_files=sources)
        start=time.monotonic()
        try:
            cmd=[sys.executable,'-m','last.extract','--video',str(video),'--key',str(a.run/'secret.key'),'--model-dir',str(a.model_dir),'--family',a.family,'--output',str(decoded)]
            with (out/'reader.log').open('ab') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            prediction=json.loads(decoded.read_text())
            if source_digest()!=sources or any(digest(Path(path))!=expected for path,expected in inputs.items()):raise ValueError('Stress inputs or source changed during extraction')
            measured=recount(prediction,np.load(a.run/'message.npy',allow_pickle=False),attack['received_sha256'],a.family)
            result['decoded_sha256']=digest(decoded)
            result.update(status='completed',**measured,bch_success=prediction['bch_success'],route=prediction['route'],groups=prediction['groups'])
        except Exception:result.update(status='failed',error=traceback.format_exc());failed=True
        result['seconds']=time.monotonic()-start
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2));temp.replace(receipt)
        print(result['attack'],result['status'],result.get('correct_bits'),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
