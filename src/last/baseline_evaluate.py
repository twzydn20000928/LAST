"""Evaluate native baselines with the same exported attacks used by LAST."""
import argparse, hashlib, json, os, subprocess, sys, time, traceback
from pathlib import Path
import numpy as np
import shutil
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
    p.add_argument('--retry-condition', choices=('clean','noise','compression','blur','drop','insert','clip'))
    p.add_argument('--retry-output', type=Path, help='New private directory for a single failed extraction')
    a=p.parse_args();os.umask(0o077)
    if bool(a.retry_condition) != bool(a.retry_output):
        p.error('--retry-condition and --retry-output must be supplied together')
    run=a.run.resolve();generation=json.loads((run/'receipt.json').read_text())
    method=generation['method'];mode=generation['mode'];family=generation.get('family')
    if generation.get('status')!='completed_generation_only' or family not in ('hunyuan','wan22'):
        raise ValueError('Require completed native Hunyuan or Wan generation')
    if method not in ('sigmark','videoshield','videomark'):raise ValueError('Unsupported native method')
    video=run/'marked.mp4';source_sha=hashlib.sha256(video.read_bytes()).hexdigest()
    if source_sha!=generation['video_sha256']:raise ValueError('Generation MP4 changed')
    state=run/'maintained_private.pkl';state_sha=hashlib.sha256(state.read_bytes()).hexdigest()
    truth_bytes = (run/'message.bin').read_bytes()
    if len(truth_bytes) != 64:
        raise ValueError('Expected 512 information bits in the source message')
    message_sha = hashlib.sha256(truth_bytes).hexdigest()
    for field, actual in [('state_sha256', state_sha), ('message_sha256', message_sha)]:
        if field in generation and generation[field] != actual:
            raise ValueError(f'Generation {field} differs from evaluation inputs')
    truth = np.unpackbits(np.frombuffer(truth_bytes, dtype=np.uint8))
    frames=load_mp4(video);directory=evaluation_directory(run,a.map_seed);directory.mkdir(exist_ok=True)
    original_directory = directory
    if a.retry_condition:
        original = json.loads((directory / (a.retry_condition + '.json')).read_bytes())
        check_cached(original, a.video_id, method, source_sha, a.map_seed)
        if (original['status'] != 'failed' or original['condition'] != a.retry_condition
                or original.get('family', 'hunyuan') != family or original['state_sha256'] != state_sha):
            raise ValueError('Retry requires a matching failed attack receipt')
        original_video = video if a.retry_condition == 'clean' else directory / (a.retry_condition + '.mp4')
        verify_received(original, original_video)
        directory = a.retry_output.resolve()
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name in ((a.retry_condition,) if a.retry_condition else ('clean','noise','compression','blur','drop','insert','clip')):
        receipt=directory/(name+'.json')
        if receipt.exists():
            cached=json.loads(receipt.read_text());check_cached(cached,a.video_id,method,source_sha,a.map_seed)
            if cached.get('condition')!=name or cached.get('state_sha256')!=state_sha:raise ValueError('Cached native state mismatch')
            # Historical Hunyuan attack receipts predate the family field.
            if cached.get('family','hunyuan')!=family:raise ValueError('Cached native family mismatch')
            if cached['status']=='completed':
                if cached.get('message_sha256',message_sha)!=message_sha:
                    raise ValueError('Cached score was computed against a different message')
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
            received=video if name=='clean' else directory/(name+'.mp4')
            if a.retry_condition:
                mapping = original['attack_map']
                row['retry_of_sha256'] = hashlib.sha256((original_directory / (name+'.json')).read_bytes()).hexdigest()
                if name != 'clean':
                    shutil.copyfile(original_video, received)
                    verify_received(original, received)
                    row['codec_command'] = original['codec_command']
            else:
                edited,mapping=attacked(frames,name,a.video_id,seed=a.map_seed if temporal else 0)
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
            receipt_bytes=(extraction/'receipt.json').read_bytes()
            extracted=json.loads(receipt_bytes)
            check_extraction(extracted,method,mode,received_sha,state_sha,temporal,family)
            verify_received(row,received)
            if hashlib.sha256(state.read_bytes()).hexdigest()!=state_sha:raise ValueError('Native state changed during extraction')
            decoded = (extraction/'decoded.bin').read_bytes()
            decoded_sha = hashlib.sha256(decoded).hexdigest()
            if 'decoded_sha256' in extracted and decoded_sha != extracted['decoded_sha256']:
                raise ValueError('Decoded bytes differ from the extraction receipt')
            prediction=np.unpackbits(np.frombuffer(decoded,dtype=np.uint8))
            if len(prediction)!=512 or len(truth)!=512:raise ValueError('Expected 512 information bits')
            row.update(status='completed',correct_bits=int((truth==prediction).sum()),total_bits=512,
                       exact_message=bool(np.array_equal(truth,prediction)),
                       decoded_sha256=decoded_sha, message_sha256=message_sha,
                       extraction_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest())
            save();print(name,row['correct_bits'],flush=True)
        except BaseException:
            row.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
