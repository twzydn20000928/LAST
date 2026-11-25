"""Prompt-cluster bootstrap, retaining all videos and attack maps in each draw."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def cluster_mean_interval(sums, counts, draws=10000, seed=0):
    """Bootstrap whole clusters, weighting each retained video or trial equally."""
    sums = np.asarray(sums)
    counts = np.asarray(counts)
    estimate = sums.sum(axis=0) / counts.sum()
    if len(counts) < 2:
        return estimate, None
    rng = np.random.Generator(np.random.PCG64(seed))
    sampled = rng.integers(0, len(counts), (draws, len(counts)))
    means = sums[sampled].sum(axis=1) / counts[sampled].sum(axis=1)[:, None]
    return estimate, np.quantile(means, [0.025, 0.975], axis=0).T.tolist()

def observations(rows,cluster_by_id,map_seeds):
    expected={(video,seed) for video in cluster_by_id for seed in map_seeds};found={}
    for row in rows:
        identity=(row['video_id'],row.get('map_seed',0))
        if identity in found:raise ValueError('Duplicate video/map observation')
        if row.get('status')!='completed':raise ValueError('Incomplete observation; no final interval')
        correct=row['correct_bits'];total=row['total_bits']
        if type(correct)!=int or type(total)!=int or total!=512 or not 0<=correct<=total:raise ValueError('Invalid512bit observation')
        if 'exact_message' in row and row['exact_message']!=(correct==512):raise ValueError('Inconsistent message recovery')
        found[identity]=np.array([correct/512,float(correct==512)])
    if set(found)!=expected:raise ValueError('Missing or extra planned video/map observations')
    if len({r.get('method') for r in rows})>1 or len({r.get('condition') for r in rows})>1:raise ValueError('One method/condition per input required')
    return found

def summarize(rows,cluster_by_id,map_seeds=(0,),paired_rows=None,draws=10000,seed=0):
    if draws<100 or not cluster_by_id or not map_seeds or len(set(map_seeds))!=len(map_seeds) or any(type(s)!=int or s not in range(5) for s in map_seeds):raise ValueError('Invalid bootstrap plan')
    first=observations(rows,cluster_by_id,map_seeds)
    second=observations(paired_rows,cluster_by_id,map_seeds) if paired_rows is not None else None
    if paired_rows is not None:
        for field in ('condition','family','mode'):
            if {r.get(field) for r in rows}!={r.get(field) for r in paired_rows}:raise ValueError(f'Paired {field} mismatch')
    clusters=sorted(set(cluster_by_id.values()));sums=[];counts=[]
    for cluster in clusters:
        ids=[identity for identity in sorted(first) if cluster_by_id[identity[0]]==cluster]
        sums.append(sum((first[i]-(second[i] if second is not None else 0) for i in ids),np.zeros(2)));counts.append(len(ids))
    estimate,intervals=cluster_mean_interval(sums,counts,draws,seed)
    return dict(metric='paired_difference_first_minus_second' if second is not None else 'rate',bit_accuracy=float(estimate[0]),message_recovery=float(estimate[1]),bit_accuracy_ci95=intervals[0] if intervals else None,message_recovery_ci95=intervals[1] if intervals else None,prompt_clusters=len(clusters),videos=len(cluster_by_id),video_map_trials=len(first),map_seeds=list(map_seeds),bootstrap_draws=draws,bootstrap_seed=seed,methodology='Percentile95% prompt-cluster bootstrap; whole clusters resampled with replacement; all their videos/maps retained; paired comparisons share the resampled clusters',limitation='One cluster cannot support an interval; few clusters yield unstable intervals. No independence assumption across bits or maps.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','rows','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--paired-rows',type=Path);p.add_argument('--map-seeds',nargs='+',type=int,default=[0]);p.add_argument('--draws',type=int,default=10000);p.add_argument('--seed',type=int,default=0);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text())
    cluster_by_id={r['id']:hashlib.sha256(r['prompt'].strip().encode()).hexdigest() for r in manifest['samples']}
    if len(cluster_by_id)!=len(manifest['samples']):raise ValueError('Duplicate manifest IDs')
    result=summarize(json.loads(a.rows.read_text()),cluster_by_id,a.map_seeds,json.loads(a.paired_rows.read_text()) if a.paired_rows else None,a.draws,a.seed)
    result.update(manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),rows_sha256=hashlib.sha256(a.rows.read_bytes()).hexdigest())
    if a.paired_rows:result['paired_rows_sha256']=hashlib.sha256(a.paired_rows.read_bytes()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':main()
