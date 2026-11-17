"""Integer bit-error accounting and message-level BCH outcomes, with coverage."""
import argparse,hashlib,json,math
from pathlib import Path
from statistics import NormalDist
from .report import CONDITIONS


def wilson(successes,total):
    if not total:return None
    z=NormalDist().inv_cdf(.975);p=successes/total;d=1+z*z/total
    mid=(p+z*z/(2*total))/d;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [max(0,mid-half),min(1,mid+half)]


def summarize(rows,expected_ids):
    if len(set(expected_ids))!=len(expected_ids):raise ValueError('Duplicate planned IDs')
    seen=set();valid=[];incomplete=[]
    for row in rows:
        identity=row['video_id']
        if identity not in expected_ids or identity in seen:raise ValueError('Extra or duplicate video')
        seen.add(identity)
        if row.get('status')!='completed':incomplete.append(identity);continue
        n=row['correct_bits'];pre=row.get('raw_information_correct')
        if row.get('total_bits')!=512 or type(n)!=int or not 0<=n<=512:raise ValueError('Invalid bit counts')
        if row.get('exact_message')!=(n==512):raise ValueError('Invalid exact-message flag')
        if type(row.get('bch_success'))!=bool:raise ValueError('This report requires explicit BCH decoder status')
        if pre is not None and (type(pre)!=int or not 0<=pre<=512):raise ValueError('Invalid pre-BCH bit count')
        valid.append(row)
    incomplete+=sorted(set(expected_ids)-seen)
    errors=sorted(512-r['correct_bits'] for r in valid);count=len(valid)
    exact=sum(e==0 for e in errors);wrong_accepted=sum(r['correct_bits']<512 and r['bch_success'] for r in valid)
    wrong_rejected=sum(r['correct_bits']<512 and not r['bch_success'] for r in valid)
    exact_failed=sum(r['correct_bits']==512 and not r['bch_success'] for r in valid)
    assert exact+wrong_accepted+wrong_rejected==count
    complete=bool(expected_ids) and not incomplete
    pre_available=sum(r.get('raw_information_correct') is not None for r in valid)
    pre_errors=sum(512-r['raw_information_correct'] for r in valid) if pre_available==count and count else None
    accuracy=1-sum(errors)/(512*count) if count else None
    recovery=exact/count if count else None
    return dict(expected=len(expected_ids),completed=count,complete=complete,incomplete_ids=incomplete,
                post_bch_error_bits=sum(errors),pre_bch_error_bits=pre_errors,pre_bch_observations=pre_available,
                observed_bit_accuracy=accuracy,final_bit_accuracy=accuracy if complete else None,
                exact_messages=exact,wrong_decoder_failure=wrong_rejected,wrong_decoder_success=wrong_accepted,
                exact_despite_decoder_failure=exact_failed,decoder_failures=wrong_rejected+exact_failed,
                observed_message_recovery=recovery,final_message_recovery=recovery if complete else None,
                observed_mrr_wilson95=wilson(exact,count),
                post_bch_ber_quantiles={name:errors[min(count-1,math.ceil(q*count)-1)]/512 if count else None
                                       for name,q in [('median',.5),('p95',.95),('p99',.99),('max',1)]},
                error_histogram={str(e):errors.count(e) for e in sorted(set(errors))},
                interpretation='Exact + wrong/decoder-failure + wrong/decoder-success partition evaluated videos. Decoder failure can still return correct systematic bits. Wilson intervals are descriptive clip-level bounds, not cluster-aware paired inference or authentication.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--method',choices=['last','lfg','lfg-c'],required=True)
    p.add_argument('--map-seed',type=int,choices=range(5),default=0);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());ids=[r['id'] for r in manifest['samples']];root=a.root.resolve()
    result=dict(family=a.family,mode=a.mode,method=a.method,map_seed=a.map_seed,
                manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),conditions={},receipt_sha256={})
    for condition in CONDITIONS:
        rows=[]
        for identity in ids:
            folder='attacks' if a.map_seed==0 else f'attacks-map-{a.map_seed}'
            path=(root/a.family/a.mode/a.method/identity/folder/(condition+'.json')).resolve()
            if not path.is_relative_to(root):raise ValueError('Unsafe sample path')
            if path.exists():
                row=json.loads(path.read_text())
                if row.get('video_id')!=identity or row.get('condition')!=condition or row.get('method',a.method)!=a.method or row.get('map_seed',0)!=a.map_seed:
                    raise ValueError('Receipt identity mismatch')
                rows.append(row);result['receipt_sha256'][str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        result['conditions'][condition]=summarize(rows,ids)
    result['complete']=all(r['complete'] for r in result['conditions'].values())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(dict(complete=result['complete'],completed={k:v['completed'] for k,v in result['conditions'].items()})))


if __name__=='__main__':main()
