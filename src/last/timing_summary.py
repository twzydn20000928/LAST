"""Across-video extraction latency statistics from repeated timing receipts."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np


def summarize(rows, expected_ids, draws=10000, seed=0):
    if not expected_ids or len(set(expected_ids)) != len(expected_ids):
        raise ValueError('Expected unique nonempty sample IDs')
    if draws < 1:raise ValueError('Positive bootstrap draw count required')
    by_id={}
    for row in rows:
        identity=row['video_id']
        if identity not in expected_ids or identity in by_id:
            raise ValueError('Unexpected or duplicate video')
        by_id[identity]=row
    values=[];missing=[];failed=[];identity_set=set()
    for identity in expected_ids:
        row=by_id.get(identity)
        if row is None:missing.append(identity);continue
        if row.get('status')!='completed':failed.append(identity);continue
        if row.get('protocol')!='supplement' or row.get('warmups')!=2 or row.get('repeats')!=5:
            raise ValueError('Require two warmups and five measured repeats')
        times=np.asarray(row['seconds'],dtype=float)
        if times.shape!=(5,) or not np.isfinite(times).all() or (times<=0).any():
            raise ValueError('Invalid timing repeats')
        identity_set.add((row['family'],row['method'],row['condition'],row['gpu']))
        values.append(dict(video_id=identity,median_seconds=float(np.median(times))))
    if len(identity_set)>1:raise ValueError('Mixed family/method/condition/hardware')
    complete=not missing and not failed
    result=dict(complete=complete,expected=len(expected_ids),completed=len(values),missing=missing,failed=failed,
                per_video=values,median_seconds=None,iqr_seconds=None,median_ci95_seconds=None,
                bootstrap=dict(unit='video',draws=draws,seed=seed,statistic='median of per-video medians'))
    if not complete:return result
    medians=np.asarray([v['median_seconds'] for v in values])
    result['median_seconds']=float(np.median(medians))
    result['iqr_seconds']=np.quantile(medians,[.25,.75]).tolist()
    if len(medians)>1:
        rng=np.random.Generator(np.random.PCG64(seed))
        sampled=np.median(medians[rng.integers(0,len(medians),(draws,len(medians)))],axis=1)
        result['median_ci95_seconds']=np.quantile(sampled,[.025,.975]).tolist()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--subsets',type=Path,default=Path('configs/paper_subsets.json'))
    p.add_argument('--index',type=Path,required=True,help='JSON list: video_id, condition, receipt path')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();index=json.loads(a.index.read_text());rows=[];evidence=[]
    for item in index:
        path=Path(item['receipt'])
        if not path.is_absolute():path=a.index.parent/path
        row=json.loads(path.read_text())
        if 'video_id' in row and row['video_id']!=item['video_id']:raise ValueError('Receipt sample mismatch')
        if 'condition' in row and row['condition']!=item['condition']:raise ValueError('Receipt condition mismatch')
        rows.append(dict(row,video_id=item['video_id'],condition=item['condition']))
        evidence.append(dict(video_id=item['video_id'],receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result=summarize(rows,json.loads(a.subsets.read_text())['supplement_timing_30'])
    result.update(scope='One method/family/condition extraction distribution; not paired generation overhead',
                  index_sha256=hashlib.sha256(a.index.read_bytes()).hexdigest(),
                  subsets_sha256=hashlib.sha256(a.subsets.read_bytes()).hexdigest(),receipts=evidence)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(complete=result['complete'],completed=result['completed'],expected=result['expected'])))


if __name__=='__main__':main()
