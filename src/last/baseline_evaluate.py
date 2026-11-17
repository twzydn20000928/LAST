"""Evaluate native baselines with the same exported attacks used by LAST."""
import argparse, hashlib, json, os, subprocess, sys, time, traceback
from pathlib import Path
import numpy as np
from .evaluate import attacked, evaluation_directory, check_cached, verify_received
from .video import load_mp4, export_mp4


def check_extraction(record, method, mode, video_sha, state_sha, temporal, family='hunyuan'):
    if family not in ('hunyuan','wan22'):raise ValueError('Unsupported native family')
    expected=dict(status='completed_extraction',method=method,mode=mode,family=family,
                  video_sha256=video_sha,state_sha256=state_sha,temporal=temporal)
    if any(record.get(k)!=v for k,v in expected.items()):
        raise ValueError('Extraction is incomplete or belongs to different video/state/method')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','upstream','model-dir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--video-id',required=True)
    p.add_argument('--map-seed',type=int,choices=range(5),default=0)
    p.add_argument('--memory-gib',type=float,default=8)
    p.add_argument('--clean-extraction',type=Path)
    a=p.parse_args();os.umask(0o077)
    run=a.run.resolve();generation=json.loads((run/'receipt.json').read_text())
    method=generation['method'];mode=generation['mode'];family=generation.get('family')
    if generation.get('status')!='completed_generation_only' or family not in ('hunyuan','wan22'):
        raise ValueError('Require completed native Hunyuan or Wan generation')
    if method not in ('sigmark','videoshield','videomark'):raise ValueError('Unsupported native method')
    video=run/'marked.mp4';source_sha=hashlib.sha256(video.read_bytes()).hexdigest()
    if source_sha!=generation['video_sha256']:raise ValueError('Generation MP4 changed')
    state=run/'maintained_private.pkl';state_sha=hashlib.sha256(state.read_bytes()).hexdigest()
    frames=load_mp4(video);directory=evaluation_directory(run,a.map_seed);directory.mkdir(exist_ok=True)
    for name in ('clean','noise','compression','blur','drop','insert','clip'):
        receipt=directory/(name+'.json')
        if receipt.exists():
            cached=json.loads(receipt.read_text());check_cached(cached,a.video_id,method,source_sha,a.map_seed)
            if cached.get('condition')!=name or cached.get('state_sha256')!=state_sha:raise ValueError('Cached native state mismatch')
            # Historical Hunyuan attack receipts predate the family field.
            if cached.get('family','hunyuan')!=family:raise ValueError('Cached native family mismatch')
            if cached['status']=='completed':
                verify_received(cached,video if name=='clean' else directory/(name+'.mp4'))
                continue
            raise ValueError('Unfinished prior condition; inspect preserved failure before retry')
        started=time.monotonic()
        row=dict(status='running',condition=name,video_id=a.video_id,method=method,map_seed=a.map_seed,
                 source_sha256=source_sha,state_sha256=state_sha,family=family)
        def save():
            row['seconds']=time.monotonic()-started
            temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2));temp.replace(receipt)
        save()
        try:
            temporal=name in ('drop','insert','clip')
            edited,mapping=attacked(frames,name,a.video_id,seed=a.map_seed if temporal else 0)
            received=video if name=='clean' else directory/(name+'.mp4')
            if name!='clean':row['codec_command']=export_mp4(edited,received,crf=28 if name=='compression' else 18)
            received_sha=hashlib.sha256(received.read_bytes()).hexdigest()
            row.update(attack_map=mapping,received_sha256=received_sha,frames=len(load_mp4(received)))
            extraction=a.clean_extraction.resolve() if name=='clean' and a.clean_extraction else directory/(name+'-extract')
            if not (name=='clean' and a.clean_extraction):
                cmd=[sys.executable,'-m','last.baseline_extract','--method',method,'--mode',mode,'--family',family,
                     '--upstream',str(a.upstream.resolve()),'--model-dir',str(a.model_dir.resolve()),
                     '--video',str(received),'--state',str(state),'--output',str(extraction),
                     '--memory-gib',str(a.memory_gib)]
                if temporal:cmd.append('--temporal')
                # No edit mapping or separate ground-truth file is supplied.
                subprocess.run(cmd,check=True)
            extracted=json.loads((extraction/'receipt.json').read_text())
            check_extraction(extracted,method,mode,received_sha,state_sha,temporal,family)
            verify_received(row,received)
            if hashlib.sha256(state.read_bytes()).hexdigest()!=state_sha:raise ValueError('Native state changed during extraction')
            prediction=np.unpackbits(np.frombuffer((extraction/'decoded.bin').read_bytes(),dtype=np.uint8))
            truth=np.unpackbits(np.frombuffer((run/'message.bin').read_bytes(),dtype=np.uint8))
            if len(prediction)!=512 or len(truth)!=512:raise ValueError('Expected 512 information bits')
            row.update(status='completed',correct_bits=int((truth==prediction).sum()),total_bits=512,
                       exact_message=bool(np.array_equal(truth,prediction)),
                       extraction_receipt_sha256=hashlib.sha256((extraction/'receipt.json').read_bytes()).hexdigest())
            save();print(name,row['correct_bits'],flush=True)
        except BaseException:
            row.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()

