"""CUDA-event ELMC timing on a saved real generation endpoint, not total overhead."""
import argparse,hashlib,json,os,statistics
from pathlib import Path
from .reader_timing import require_exclusive


def event_times(operation,event_factory,synchronize,guard,warmups=2,repeats=5):
    if warmups<1 or repeats<1:raise ValueError('Positive warmups and repeats required')
    for _ in range(warmups):
        guard();operation();synchronize();guard()
    values=[]
    for _ in range(repeats):
        guard();synchronize();start=event_factory();end=event_factory()
        start.record();result=operation();end.record();end.synchronize()
        seconds=start.elapsed_time(end)/1000
        guard()
        if seconds<=0:raise ValueError('Nonpositive CUDA-event duration')
        values.append(seconds)
        del result
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.umask(0o077)
    if a.output.exists():raise ValueError('Use a new output file')
    require_exclusive()
    import numpy as np
    import torch
    from .elmc import embed
    from .coding import BCH512
    generation=json.loads((a.run/'receipt.json').read_text())
    if generation.get('status')!='completed' or generation.get('method')!='last':raise ValueError('Require completed LAST run')
    endpoint=a.run/'endpoint.pt'
    sha=hashlib.sha256(endpoint.read_bytes()).hexdigest()
    if generation.get('endpoint_sha256')!=sha:raise ValueError('Missing or mismatched saved endpoint provenance')
    z=torch.load(endpoint,weights_only=True,map_location='cpu')
    if z.shape!=(1,16,17,64,64) or not torch.isfinite(z).all():raise ValueError('Invalid endpoint')
    z=z.float().cuda();codes=torch.load(a.run/'codes.pt',weights_only=True,map_location='cpu').float().cuda()
    signs=torch.from_numpy(BCH512().encode(np.load(a.run/'message.npy')).astype(np.float32)*2-1).cuda()
    torch.set_num_threads(4)
    with torch.inference_mode():
        times=event_times(lambda:embed(z,codes,signs,mu=generation.get('mu',.5),fixed_target=generation.get('fixed_target',False),uniform=generation.get('uniform_profile',False)),
                          lambda:torch.cuda.Event(enable_timing=True),torch.cuda.synchronize,require_exclusive)
    result=dict(status='completed',scope='CUDA-event ELMC call with resident inputs; not paired full-generation overhead',
                endpoint_sha256=sha,generation_receipt_sha256=hashlib.sha256((a.run/'receipt.json').read_bytes()).hexdigest(),
                codes_sha256=hashlib.sha256((a.run/'codes.pt').read_bytes()).hexdigest(),
                implementation_sha256={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('embedding_timing.py','elmc.py','reader_timing.py')},
                warmups=2,repeats=5,seconds=times,median_seconds=statistics.median(times),iqr_seconds=np.quantile(times,[.25,.75]).tolist(),
                gpu=torch.cuda.get_device_name(0),torch_version=torch.__version__,cuda_version=torch.version.cuda,
                includes='Entire public embed call: transforms, margin update, allocations and validation',
                excludes='Model load, generation, VAE decode, export, disk IO, key preparation and host-to-device input transfers')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status='completed',median_seconds=result['median_seconds'])))


if __name__=='__main__':main()
