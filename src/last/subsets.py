"""Metadata-only deterministic primary subsetting for ablation and timing."""
import argparse,hashlib,json
from collections import defaultdict
from pathlib import Path
from .data import validate

def select(manifest,count=30):
    validate(manifest)
    if not 1<=count<=len(manifest['samples']):raise ValueError('Invalid subset size')
    rank=lambda value:hashlib.sha256(('LAST-paper-subsets-v1\0'+value).encode()).hexdigest()
    groups=defaultdict(list)
    for row in manifest['samples']:groups[row['dimension']].append(row)
    groups={dim:sorted(rows,key=lambda r:rank(r['id'])) for dim,rows in groups.items()}
    order=sorted(groups,key=rank);chosen=[];offset=0
    while len(chosen)<count:
        for dim in order:
            if offset<len(groups[dim]):chosen.append(groups[dim][offset]['id'])
            if len(chosen)==count:break
        offset+=1
    return chosen

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());ids=select(manifest)
    result=dict(schema_version=1,manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),rule='SHA256 LAST-paper-subsets-v1 domain, round-robin over dimensions and ranked sample IDs; no metrics input',ablation_i2v_30=ids,supplement_timing_30=ids,main_timing_1=ids[:1],selection_disclosure='Reconstruction choice: paper gives sample counts but not IDs. Frozen after the first primary sample was measured; selection uses metadata only and does not tune main parameters.',development_sweep='Separate disjoint development manifest required; primary IDs are not used for tuning')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({'ablation':len(ids),'timing':len(ids)}))

if __name__=='__main__':main()
