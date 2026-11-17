"""Freeze disjoint development prompts without reading any measured outcomes."""
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path
from .data import validate
from .upstream import verify

SALT='LAST-paper-v1-development-20261118'
def normalize(text):return ' '.join(text.casefold().split())
def rank(text):return hashlib.sha256((SALT+'|'+text).encode()).hexdigest()


def select(primary, prompts):
    validate(primary)
    excluded={normalize(r['prompt']) for r in primary['samples']}
    pools=defaultdict(list)
    for dimension,lines in prompts.items():
        for i,text in enumerate(lines):
            text=text.strip();key=normalize(text)
            if text and key not in excluded:pools[dimension].append((rank(dimension+'|'+key),i,text,key))
        pools[dimension].sort()
    chosen=[];used=set(excluded);dimensions=sorted(pools)
    while len(chosen)<20:
        before=len(chosen)
        for dimension in dimensions:
            candidate=next((r for r in pools[dimension] if r[3] not in used),None)
            if candidate:
                _,line,prompt,key=candidate;used.add(key)
                chosen.append(dict(dimension=dimension,source_line=line,prompt=prompt))
            if len(chosen)==20:break
        if len(chosen)==before:raise ValueError('Not enough disjoint development prompts')
    rows=[]
    for prompt_index,prompt in enumerate(chosen):
        for replicate in range(4):
            i=len(rows)
            rows.append(dict(id=f'dev-{i:03d}',index=i,**prompt,replicate=replicate,
                             seed=2026111800+i,key_slot=i%8,image=None))
    return dict(schema_version=1,split='development',selection_salt=SALT,
                selection='SHA256-ranked per-dimension round robin; 20 distinct prompts x 4 seeds; no metric access',
                disjointness='Casefold/whitespace normalized exact text; not a semantic-independence claim',
                conditioning='I2V conditioning images pending; do not substitute primary images',
                private_state='Create eight new development keys; never reuse primary keys',
                margin_sweep_ids=[rows[i]['id'] for i in (0,4,8)],samples=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary',type=Path,default=Path('configs/primary_manifest.json'))
    p.add_argument('--metadata-manifest',type=Path,default=Path('configs/quality_metadata_manifest.json'))
    p.add_argument('--metadata-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.metadata_root,json.loads(a.metadata_manifest.read_text()))
    prompt_dir=a.metadata_root/'prompt_set/VBench2_aug_prompt'
    primary=json.loads(a.primary.read_text())
    dimensions=sorted({r['dimension'] for r in primary['samples']})
    paths={d:prompt_dir/(d+'.txt') for d in dimensions}
    result=select(primary,{d:path.read_text().splitlines() for d,path in paths.items()})
    result['source']=dict(primary_sha256=hashlib.sha256(a.primary.read_bytes()).hexdigest(),
                          prompt_file_sha256={d:hashlib.sha256(f.read_bytes()).hexdigest() for d,f in paths.items()})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(samples=len(result['samples']),prompts=20,i2v_ready=False)))


if __name__=='__main__':main()
