"""Coverage-aware paired PSNR/SSIM table; never substitutes for V-score."""
import argparse,hashlib,json,math
from collections import defaultdict
from pathlib import Path


def summarize(rows, expected):
    if not expected or len(set(expected))!=len(expected):raise ValueError('Expected unique sample IDs')
    seen=set();definitions=set();valid=[]
    for row in rows:
        identity=row['video_id']
        if identity in seen or identity not in expected:raise ValueError('Duplicate or unexpected sample')
        seen.add(identity);mse=row['rgb_mse'];ssim=row['ssim'];psnr=row['psnr_db']
        if row['frames']!=65 or not math.isfinite(mse) or not 0<=mse<=1 or not math.isfinite(ssim) or not -1<=ssim<=1:
            raise ValueError('Invalid fidelity metric or frame count')
        if row['identical']!=(mse==0):raise ValueError('Inconsistent identical flag')
        if mse==0:
            if psnr is not None:raise ValueError('Identical PSNR must use null plus flag')
        elif psnr is None or not math.isclose(psnr,-10*math.log10(mse),rel_tol=1e-8,abs_tol=1e-8):
            raise ValueError('PSNR does not match MSE')
        if not row.get('definition'):raise ValueError('Missing metric definition')
        definitions.add(row['definition']);valid.append(row)
    if len(definitions)>1:raise ValueError('Mixed metric definitions')
    count=len(valid);complete=count==len(expected);identical=sum(r['identical'] for r in valid)
    mean_mse=sum(r['rgb_mse'] for r in valid)/count if count else None
    mean_psnr=sum(r['psnr_db'] for r in valid)/count if count and not identical else None
    mean_ssim=sum(r['ssim'] for r in valid)/count if count else None
    return dict(expected=len(expected),completed=count,missing=[i for i in expected if i not in seen],complete=complete,
                identical_pairs=identical,observed_mean_video_psnr_db=mean_psnr,observed_mean_video_psnr_is_infinite=bool(identical),
                observed_mean_ssim=mean_ssim,observed_mean_mse=mean_mse,
                observed_psnr_from_mean_mse_db=-10*math.log10(mean_mse) if mean_mse else None,
                final_mean_video_psnr_db=mean_psnr if complete else None,
                final_mean_video_psnr_is_infinite=bool(identical) if complete else None,
                final_mean_ssim=mean_ssim if complete else None,
                metric_definition=next(iter(definitions)) if definitions else None)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();plan=json.loads(a.plan.read_text());groups=defaultdict(lambda:dict(expected=[],rows=[]));evidence=[]
    for item in plan['runs']:
        group=groups[(item['family'],item['mode'],item['method'])];group['expected'].append(item['video_id'])
        folder=(root/item['run']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Unsafe run path')
        path=folder/'quality.json'
        if not path.exists():continue
        row=json.loads(path.read_text());generation=json.loads((folder/'receipt.json').read_text())
        if generation.get('status')!='completed' or any(generation.get(k)!=item[k] for k in ('family','mode','method')):
            raise ValueError('Quality pair generation identity mismatch')
        for name in ('reference','marked'):
            if hashlib.sha256((folder/(name+'.mp4')).read_bytes()).hexdigest()!=row[name+'_sha256']:raise ValueError('Quality pair video changed')
        group['rows'].append(dict(row,video_id=item['video_id']))
        evidence.append(dict(run=item['run'],receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    cells=[dict(family=k[0],mode=k[1],method=k[2],**summarize(v['rows'],v['expected'])) for k,v in sorted(groups.items())]
    result=dict(scope='Paired fidelity only; not V-score, aesthetic quality or temporal perception',complete=bool(cells) and all(c['complete'] for c in cells),
                cells=cells,receipts=evidence,plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(complete=result['complete'],completed=sum(c['completed'] for c in cells),expected=sum(c['expected'] for c in cells))))


if __name__=='__main__':main()
