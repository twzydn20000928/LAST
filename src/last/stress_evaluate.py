"""Evaluate exported stress videos using an isolated blind LAST extraction CLI."""
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np

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
    folders=sorted(path.parent for path in a.attacks.glob('*/attack.json'))
    if not folders:raise ValueError('No exported stress conditions')
    failed=False
    for folder in folders:
        attack,video=verify_attack(folder,source_sha);out=a.output/folder.name;out.mkdir(exist_ok=True,mode=0o700)
        receipt=out/'evaluation.json'
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            if prior.get('received_sha256')!=attack['received_sha256']:raise ValueError('Existing evaluation belongs to another video')
            if prior.get('status')=='completed':continue
            receipt.rename(out/f'evaluation.failed-{time.time_ns()}.json')
        decoded=out/'decoded_private.json'
        # Preserve any unsuccessful prior extraction output; never silently reuse it.
        if decoded.exists():decoded.rename(out/f'decoded.previous-{time.time_ns()}.json')
        result=dict(status='running',attack=attack['attack'],seed=attack['seed'],video_id=attack['video_id'],source_sha256=source_sha,received_sha256=attack['received_sha256'])
        start=time.monotonic()
        try:
            cmd=[sys.executable,'-m','last.extract','--video',str(video),'--key',str(a.run/'secret.key'),'--model-dir',str(a.model_dir),'--family',a.family,'--output',str(decoded)]
            with (out/'reader.log').open('ab') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            prediction=json.loads(decoded.read_text())
            if prediction['video_sha256']!=attack['received_sha256'] or prediction['information_bits']!=512:raise ValueError('Decoded output identity mismatch')
            bits=np.unpackbits(np.frombuffer(bytes.fromhex(prediction['message_hex']),dtype=np.uint8))
            truth=np.load(a.run/'message.npy')
            if bits.shape!=(512,) or truth.shape!=(512,):raise ValueError('Wrong information payload')
            result.update(status='completed',correct_bits=int((bits==truth).sum()),total_bits=512,exact_message=bool(np.array_equal(bits,truth)),bch_success=prediction['bch_success'],route=prediction['route'],groups=prediction['groups'])
        except Exception:result.update(status='failed',error=traceback.format_exc());failed=True
        result['seconds']=time.monotonic()-start
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2));temp.replace(receipt)
        print(result['attack'],result['status'],result.get('correct_bits'),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
