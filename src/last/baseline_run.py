"""Native Hunyuan baseline generation and isolated extraction integration."""
import argparse, hashlib, json, os, subprocess, sys, time, traceback
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['videoshield','videomark','sigmark'],required=True)
    p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    for name in ('upstream','model-dir','case','message','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--registry',type=Path)
    p.add_argument('--memory-gib',type=float,default=8)
    a=p.parse_args();os.umask(0o077)
    if a.method=='videomark' and a.registry is None:p.error('VideoMark requires --registry')
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False,mode=0o700)
    generation=output/'generation';extraction=output/'extraction'
    state=dict(status='starting',method=a.method,mode=a.mode,
               scope='Single native baseline integration; not a benchmark or exclusive timing',
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    start=time.monotonic()
    def save():
        state['seconds']=time.monotonic()-start
        temp=output/'receipt.tmp';temp.write_text(json.dumps(state,indent=2));temp.replace(output/'receipt.json')
    save()
    try:
        common=['--method',a.method,'--mode',a.mode,'--upstream',str(a.upstream.resolve()),
                '--model-dir',str(a.model_dir.resolve()),'--memory-gib',str(a.memory_gib)]
        command=[sys.executable,'-m','last.baseline_generate',*common,'--case',str(a.case.resolve()),
                 '--message',str(a.message.resolve()),'--output',str(generation)]
        if a.registry:command+=['--registry',str(a.registry.resolve())]
        state['status']='generating';save()
        subprocess.run(command,check=True)
        state['status']='extracting';save()
        # No separate truth file is supplied; each baseline retains its native
        # reference/registry access through the explicitly documented state.
        subprocess.run([sys.executable,'-m','last.baseline_extract',*common,
                        '--video',str(generation/'marked.mp4'),
                        '--state',str(generation/'maintained_private.pkl'),
                        '--output',str(extraction)],check=True)
        truth=np.unpackbits(np.frombuffer((generation/'message.bin').read_bytes(),dtype=np.uint8))
        prediction=np.unpackbits(np.frombuffer((extraction/'decoded.bin').read_bytes(),dtype=np.uint8))
        if len(truth)!=512 or len(prediction)!=512:raise ValueError('Expected 512 information bits')
        state.update(status='completed',correct_bits=int((truth==prediction).sum()),total_bits=512,
                     exact_message=bool(np.array_equal(truth,prediction)),
                     video_sha256=hashlib.sha256((generation/'marked.mp4').read_bytes()).hexdigest(),
                     generation_receipt_sha256=hashlib.sha256((generation/'receipt.json').read_bytes()).hexdigest(),
                     extraction_receipt_sha256=hashlib.sha256((extraction/'receipt.json').read_bytes()).hexdigest())
        save();print(json.dumps(state))
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
