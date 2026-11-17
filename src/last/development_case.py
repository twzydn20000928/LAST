"""Export a development case, verifying its fixed conditioning image receipt."""
import argparse,hashlib,json
from pathlib import Path
from .development import validate_development


def build(manifest,sample_id,mode,manifest_sha,conditioning=None):
    rows=manifest['samples'];matches=[i for i,r in enumerate(rows) if r['id']==sample_id]
    if len(matches)!=1:raise ValueError('Unknown or duplicate development ID')
    index=matches[0];row=rows[index]
    case=dict(prompt=row['prompt'],seed=row['seed'],video_id=row['id'],key_slot=row['key_slot'],development_manifest_sha256=manifest_sha)
    if mode=='i2v':
        if conditioning is None:raise ValueError('I2V requires a completed development conditioning directory')
        folder=Path(conditioning);receipt=folder/'receipt.json';r=json.loads(receipt.read_text());first=rows[index//4*4]
        if r.get('status')!='completed' or r.get('manifest_sha256')!=manifest_sha or any(r.get(k)!=first[v] for k,v in [('sample_id','id'),('seed','seed'),('prompt','prompt')]):
            raise ValueError('Conditioning receipt is incomplete or belongs to another prompt/split')
        image=folder/'input.png'
        if hashlib.sha256(image.read_bytes()).hexdigest()!=r.get('image_sha256'):raise ValueError('Conditioning image changed')
        case.update(image=str(image.resolve()),conditioning_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),image_sha256=r['image_sha256'])
    elif mode!='t2v':raise ValueError('Unknown mode')
    return case


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('configs/development_manifest.json'))
    p.add_argument('--primary',type=Path,default=Path('configs/primary_manifest.json'))
    p.add_argument('--sample-id',required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--conditioning',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());validate_development(manifest,json.loads(a.primary.read_text()))
    case=build(manifest,a.sample_id,a.mode,hashlib.sha256(a.manifest.read_bytes()).hexdigest(),a.conditioning)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(case,f,indent=2)


if __name__=='__main__':main()
