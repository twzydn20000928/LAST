"""Verify the frozen public manifest and resolve reader-local conditioning paths."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter,defaultdict

def validate(manifest, image_root=None):
    rows=manifest['samples']
    if len(rows)!=400:raise ValueError('Expected400primary samples')
    if len({r['id'] for r in rows})!=400:raise ValueError('Duplicate sample IDs')
    dimensions=defaultdict(lambda:defaultdict(list))
    for i,r in enumerate(rows):
        if r['index']!=i or r['seed']!=2025+i or r['key_slot']!=i%8:raise ValueError('Invalid frozen assignment')
        dimensions[r['dimension']][r['prompt']].append(r['replicate'])
    if len(dimensions)!=18:raise ValueError('Expected18dimensions')
    for dim,prompts in dimensions.items():
        n,seeds=(3,20) if dim=='Diversity' else (5,4)
        if len(prompts)!=n or any(sorted(v)!=list(range(seeds)) for v in prompts.values()):raise ValueError(f'Invalid prompt/seed allocation:{dim}')
    if Counter(r['key_slot'] for r in rows)!=dict.fromkeys(range(8),50):raise ValueError('Unbalanced keys')
    checked={}
    if image_root is not None:
        base=Path(image_root).resolve()
        for row in rows:
            rel=Path(row['image']);p=(base/rel).resolve()
            if rel.is_absolute() or not p.is_relative_to(base):raise ValueError('Unsafe image path')
            if str(p) not in checked:checked[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
            if checked[str(p)]!=row['image_sha256']:raise ValueError(f'Image checksum mismatch:{row["id"]}')
    return dict(samples=len(rows),dimensions=len(dimensions),prompt_slots=sum(map(len,dimensions.values())),unique_prompt_texts=len({r['prompt'] for r in rows}),verified_images=len(checked))

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--image-root',type=Path);p.add_argument('--case-index',type=int);p.add_argument('--case-output',type=Path);a=p.parse_args()
    m=json.loads(a.manifest.read_text());summary=validate(m,a.image_root)
    if a.case_index is not None:
        if a.image_root is None or a.case_output is None:raise ValueError('Case output requires image root and case-output')
        row=m['samples'][a.case_index]
        a.case_output.parent.mkdir(parents=True,exist_ok=True)
        a.case_output.write_text(json.dumps(dict(prompt=row['prompt'],seed=row['seed'],image=str((a.image_root/row['image']).resolve()),video_id=row['id'],key_slot=row['key_slot']),indent=2))
    print(json.dumps(summary))
if __name__=='__main__':main()
