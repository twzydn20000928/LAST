"""Probe official scorer imports in isolated offline CPU processes, not scores."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from .quality_report import CATEGORIES
from .quality_paths import scorer_paths


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,choices=range(1,5),default=2)
    p.add_argument('--timeout',type=int,default=60)
    p.add_argument('--extra-pythonpath',type=Path,action='append',default=[],help='Explicit dependency overlays, in priority order; recorded in receipt')
    a=p.parse_args();upstream=a.upstream.resolve()
    if not (upstream/'vbench2').is_dir() or a.timeout<1:p.error('Invalid upstream or timeout')
    if a.output.exists():p.error('Output exists; retain the previous audit')
    paths=[upstream]+[d.resolve() for d in a.extra_pythonpath]+scorer_paths(upstream)[1:]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    env['PYTHONPATH']=os.pathsep.join(map(str,paths))+os.pathsep+env.get('PYTHONPATH','')
    def probe(name):
        module=name.lower().replace('-','_');source=upstream/'vbench2'/(module+'.py')
        code="import importlib; from pathlib import Path; m=importlib.import_module("+repr('vbench2.'+module)+"); assert Path(m.__file__).resolve()==Path("+repr(str(source))+"); assert callable(getattr(m,"+repr('compute_'+module)+"))\n"
        code+='''import sys,json,hashlib,importlib.metadata as metadata
packages={}
for name in ('torch','torchvision','numpy','scipy','transformers','accelerate','timm','mmcv','mmengine','mmdet','modelscope','swift','llava','decord','PIL','cv2','peft','safetensors'):
    value=sys.modules.get(name)
    if value is None:continue
    path=getattr(value,'__file__',None)
    packages[name]={'loaded_version':str(getattr(value,'__version__','unknown')),'path':path,'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest() if path and Path(path).is_file() else None}
native={name:{'path':str(value.__file__),'sha256':hashlib.sha256(Path(value.__file__).read_bytes()).hexdigest()} for name,value in list(sys.modules.items()) if name.startswith('mmcv.') and str(getattr(value,'__file__','')).endswith(('.so','.pyd'))}
print('LAST_IMPORT_PROVENANCE='+json.dumps({'packages':packages,'native_extensions':native}))
'''
        start=time.monotonic()
        try:
            r=subprocess.run([sys.executable,'-c',code],cwd=upstream,env=env,capture_output=True,text=True,timeout=a.timeout)
            item=dict(status='importable' if r.returncode==0 else 'failed',returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
            markers=[line for line in r.stdout.splitlines() if line.startswith('LAST_IMPORT_PROVENANCE=')]
            if r.returncode==0:
                if len(markers)!=1:raise RuntimeError('Missing unambiguous import provenance')
                item['loaded_dependencies']=json.loads(markers[0].split('=',1)[1])
        except subprocess.TimeoutExpired:
            item=dict(status='timeout',timeout_seconds=a.timeout)
        item.update(seconds=time.monotonic()-start,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None)
        return name,item
    names=sum(CATEGORIES.values(),[])
    with ThreadPoolExecutor(max_workers=a.workers) as pool:results=dict(pool.map(probe,names))
    record=dict(scope='Import availability only; no model weights loaded intentionally and no quality scores',python=sys.executable,python_version=sys.version,upstream=str(upstream),search_paths=list(map(str,paths)),inherited_pythonpath=os.environ.get('PYTHONPATH',''),dimensions=results,all_importable=all(r['status']=='importable' for r in results.values()))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2))
    print(json.dumps({k:v['status'] for k,v in results.items()}))


if __name__=='__main__':main()
