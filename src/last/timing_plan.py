"""Freeze timing acquisition order before measurements; never fabricates durations."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

METHODS=('last','lfg','videoshield','videomark','sigmark')


def make_plan(ids,seed=20261118):
    if len(ids)!=30 or len(set(ids))!=30:
        raise ValueError('Require the thirty unique frozen timing videos')
    rng=np.random.Generator(np.random.PCG64(seed))
    readers=[];generation=[]
    for identity in rng.permutation(ids):
        # Balance AB/BA across the thirty videos for every method. Pair members
        # stay adjacent; their model, case, seed and export boundaries must match.
        for method in rng.permutation(METHODS):
            generation.append(dict(video_id=str(identity),method=str(method)))
        for condition in rng.permutation(('clean','drop')):
            for method in rng.permutation(METHODS):
                readers.append(dict(video_id=str(identity),method=str(method),condition=str(condition),warmups=2,repeats=5))
    for method in METHODS:
        orders=rng.permutation(['AB']*15+['BA']*15)
        rows=[r for r in generation if r['method']==method]
        for row,order in zip(rows,orders):
            row['order']=str(order)
            row['branches']=['reference','marked'] if order=='AB' else ['marked','reference']
    return dict(schema_version=1,status='planned_not_measured',seed=seed,rng='NumPy PCG64',
                scope='One fixed backbone/mode on an exclusive L40; instantiate separately per reported configuration',
                reconstruction='Paper requires randomized order; PCG64 seed and balanced AB/BA are explicit implementation choices',
                reader_jobs=readers,generation_pairs=generation,
                requirements=['No other GPU compute jobs during acquisition','Same paired case, model, key and message; no output-based reordering',
                              'Exclude model load, key setup and export; include full decode/readout within documented boundaries',
                              'Record failures in place; any retry is a separate attempt, never a replacement selected by speed'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--subsets',type=Path,default=Path('configs/paper_subsets.json'))
    p.add_argument('--seed',type=int,default=20261118)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    subsets=json.loads(a.subsets.read_text())
    plan=make_plan(subsets['supplement_timing_30'],a.seed)
    plan['subsets_sha256']=hashlib.sha256(a.subsets.read_bytes()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(plan,f,indent=2)
    print(json.dumps(dict(reader_jobs=len(plan['reader_jobs']),generation_pairs=len(plan['generation_pairs']),status=plan['status'])))


if __name__=='__main__':main()
