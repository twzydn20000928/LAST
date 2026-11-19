"""Across-video extraction latency statistics from repeated timing receipts."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from .temporal import attack_map


def check_drop_frames(attack, video_id):
    expected = attack_map(video_id, "drop", seed=0, frames=65, count=30)
    if attack.get("frames") != len(expected) or attack.get("attack_map") != expected:
        raise ValueError("Expected the protocol's 35 surviving frames after deletion")


def generation_summary(index, expected_ids, base):
    """Aggregate complete AB/BA measurements with the video as bootstrap unit."""
    medians={}
    settings=set()
    evidence={}
    for item in index:
        video=item['video_id']
        if video not in expected_ids or video in medians:
            raise ValueError('Unexpected or duplicate generation case')
        data=(base/item['receipt']).read_bytes()
        case_data=(base/item['case']).read_bytes()
        row=json.loads(data)
        case=json.loads(case_data)
        if (case['video_id']!=video or case['seed']!=row['seed'] or
            hashlib.sha256(case_data).hexdigest()!=row['case_sha256']):
            raise ValueError('Generation receipt case mismatch')
        if row['status']!='completed' or row['protocol']!='supplement':
            raise ValueError('Require completed supplement generation timing')
        settings.add((row['family'],row['mode'],row['method'],row['gpu']))
        m=row['measurement']
        pairs=m['pairs']
        if m['warmup_pairs']!=2 or m['measured_pairs']!=5 or len(pairs)!=5:
            raise ValueError('Require two warmup pairs and five measured pairs')
        if (row['order'] not in ('AB','BA') or row['order']!=m['order'] or
            any(p['warmup'] is not False or p['order']!=m['order'] for p in pairs) or
            [p['pair_index'] for p in pairs]!=list(range(2,7))):
            raise ValueError('Invalid measured generation pair order')
        times=np.asarray([[p['marked_seconds'],p['reference_seconds']] for p in pairs],dtype=float)
        if not np.isfinite(times).all() or (times<=0).any():
            raise ValueError('Invalid paired generation durations')
        medians[video]=dict(marked=float(np.median(times[:,0])),
                            overhead=float(np.median(times[:,0]-times[:,1])),order=m['order'])
        evidence[video]=hashlib.sha256(data).hexdigest()
    if len(settings)>1:
        raise ValueError('Mixed generation timing configurations')
    missing=[v for v in expected_ids if v not in medians]
    result=dict(complete=not missing,missing=missing,per_video=medians,receipts_sha256=evidence,
                median_generation_seconds=None,generation_iqr_seconds=None,
                median_overhead_seconds=None,overhead_ci95_seconds=None)
    if settings:
        result.update(zip(('family','mode','method','gpu'),next(iter(settings))))
    if missing:
        return result
    if sum(medians[v]['order']=='AB' for v in expected_ids)*2!=len(expected_ids):
        raise ValueError('Expected balanced AB/BA acquisition')
    marked=np.asarray([medians[v]['marked'] for v in expected_ids])
    overhead=np.asarray([medians[v]['overhead'] for v in expected_ids])
    rng=np.random.Generator(np.random.PCG64(0))
    indices=rng.integers(0,len(overhead),(10000,len(overhead)))
    result.update(median_generation_seconds=float(np.median(marked)),
                  generation_iqr_seconds=np.quantile(marked,[.25,.75]).tolist(),
                  median_overhead_seconds=float(np.median(overhead)),
                  overhead_ci95_seconds=np.quantile(np.median(overhead[indices],axis=1),[.025,.975]).tolist(),
                  bootstrap=dict(unit='video',draws=10000,seed=0))
    return result


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
        if row.get('mode') not in ('i2v','t2v'):
            raise ValueError('Timing receipt must declare i2v or t2v mode')
        if row.get('length_study_frames') is not None:
            raise ValueError('Length-study timing belongs in the separate length experiment')
        if 'temporal' in row and row['condition'] in ('clean', 'drop'):
            if row['temporal'] is not (row['condition'] == 'drop'):
                raise ValueError('Native temporal recovery setting differs from indexed timing condition')
        identity_set.add((row['family'],row['mode'],row['method'],row['condition'],row['gpu']))
        values.append(dict(video_id=identity,median_seconds=float(np.median(times))))
    if len(identity_set)>1:raise ValueError('Mixed family/mode/method/condition/hardware')
    complete=not missing and not failed
    result=dict(complete=complete,expected=len(expected_ids),completed=len(values),missing=missing,failed=failed,
                per_video=values,median_seconds=None,iqr_seconds=None,median_ci95_seconds=None,
                bootstrap=dict(unit='video',draws=draws,seed=seed,statistic='median of per-video medians'))
    if identity_set:
        result.update(zip(('family','mode','method','condition','gpu'), next(iter(identity_set))))
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
    p.add_argument('--generation',action='store_true',help='Aggregate paired generation receipts (index entries: video_id, case, receipt)')
    p.add_argument('--verify-attack-receipts',action='store_true',
                   help='Bind each completed timing to the indexed attack receipt by received MP4 hash')
    a=p.parse_args();index=json.loads(a.index.read_text());rows=[];evidence=[];seen=set()
    if a.generation:
        if a.verify_attack_receipts:p.error('Attack receipt verification applies to extraction')
        ids=json.loads(a.subsets.read_text())['supplement_timing_30']
        if len(ids)!=30 or len(set(ids))!=30:raise ValueError('Expected 30 distinct timing IDs')
        result=generation_summary(index,ids,a.index.parent)
        result.update(index_sha256=hashlib.sha256(a.index.read_bytes()).hexdigest(),
                      subsets_sha256=hashlib.sha256(a.subsets.read_bytes()).hexdigest())
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        return
    for item in index:
        path=Path(item['receipt'])
        if not path.is_absolute():path=a.index.parent/path
        data=path.read_bytes()
        fingerprint=hashlib.sha256(data).hexdigest()
        if fingerprint in seen:raise ValueError('Timing receipt reused for multiple entries')
        seen.add(fingerprint)
        row=json.loads(data)
        if 'video_id' in row and row['video_id']!=item['video_id']:raise ValueError('Receipt sample mismatch')
        if 'condition' in row and row['condition']!=item['condition']:raise ValueError('Receipt condition mismatch')
        rows.append(dict(row,video_id=item['video_id'],condition=item['condition']))
        record=dict(video_id=item['video_id'],receipt_sha256=fingerprint)
        if a.verify_attack_receipts and row.get('status')=='completed':
            attack_data=(a.index.parent / item['attack_receipt']).read_bytes()
            attack=json.loads(attack_data)
            received=row.get('received_sha256')
            if (not isinstance(received,str) or len(received)!=64 or any(c not in '0123456789abcdef' for c in received)
                or attack.get('received_sha256')!=received or attack.get('status')!='completed'
                or attack.get('video_id')!=item['video_id'] or attack.get('condition')!=item['condition']
                or attack.get('method')!=row['method'] or attack.get('map_seed')!=0):
                raise ValueError('Attack receipt does not match timed video, method or condition')
            if item['condition'] == 'drop':
                check_drop_frames(attack, item['video_id'])
            record.update(received_sha256=received,attack_receipt_sha256=hashlib.sha256(attack_data).hexdigest())
        evidence.append(record)
    result=summarize(rows,json.loads(a.subsets.read_text())['supplement_timing_30'])
    result.update(verify_attack_receipts=a.verify_attack_receipts,
                  scope='One method/family/condition extraction distribution; not paired generation overhead',
                  index_sha256=hashlib.sha256(a.index.read_bytes()).hexdigest(),
                  subsets_sha256=hashlib.sha256(a.subsets.read_bytes()).hexdigest(),receipts=evidence)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(complete=result['complete'],completed=result['completed'],expected=result['expected'])))


if __name__=='__main__':main()
