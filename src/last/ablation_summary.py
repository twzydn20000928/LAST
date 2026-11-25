"""Complete-coverage reader ablation tables from the frozen sample subset."""
import argparse,csv,hashlib,json
from pathlib import Path
from .report import CONDITIONS

# Labels in the frozen four-reader table, in manuscript order.
VARIANTS = ("full", "without_cgc", "without_sws", "without_ccta")


def summarize(rows, expected):
    if not expected or len(set(expected))!=len(expected):raise ValueError('Unique sample IDs required')
    indexed={};pairs={};writers=set();implementations=set();video_codes={};sources={}
    for row in rows:
        key=(row['video_id'],row['condition'],row['variant'])
        if key[0] not in expected or key[1] not in CONDITIONS or key[2] not in VARIANTS or key in indexed:
            raise ValueError('Unexpected or duplicate ablation observation')
        indexed[key]=row
        if row['status']!='completed':continue
        correct=row['correct_bits']
        if type(correct)!=int or row['total_bits']!=512 or not 0<=correct<=512 or row['exact_message']!=(correct==512):
            raise ValueError('Invalid bit or message counts')
        for field in ('video_sha256','source_sha256','codes_sha256','implementation_sha256','writer_method'):
            if not row.get(field):raise ValueError('Missing ablation provenance')
        writers.add(row['writer_method']);implementations.add(json.dumps(row['implementation_sha256'],sort_keys=True))
        pair=(row['video_sha256'],row['source_sha256'],row['codes_sha256'])
        if key[:2] in pairs and pairs[key[:2]]!=pair:raise ValueError('Variants did not use identical videos/codebooks')
        pairs[key[:2]]=pair
        if key[0] in sources and sources[key[0]]!=row['source_sha256']:
            raise ValueError('Source MP4 changed across attacks')
        sources[key[0]]=row['source_sha256']
        if key[0] in video_codes and video_codes[key[0]]!=row['codes_sha256']:raise ValueError('Codebook changed across attacks')
        video_codes[key[0]]=row['codes_sha256']
    if len(writers)>1 or len(implementations)>1:raise ValueError('Mixed writer or reader revisions; report separately')
    cells=[]
    for condition in CONDITIONS:
        for variant in VARIANTS:
            records=[indexed.get((v,condition,variant)) for v in expected]
            valid=[r for r in records if r and r['status']=='completed']
            missing=sum(r is None for r in records);failed=sum(r is not None and r['status']=='failed' for r in records)
            pending=len(records)-len(valid)-missing-failed
            complete=len(valid)==len(expected);correct=sum(r['correct_bits'] for r in valid);bits=512*len(valid)
            cells.append(dict(condition=condition,variant=variant,expected=len(expected),completed=len(valid),
                              missing=missing,failed=failed,pending=pending,correct_bits=correct,total_bits=bits,
                              observed_bit_accuracy=correct/bits if bits else None,
                              final_bit_accuracy=correct/bits if complete else None,
                              exact_messages=sum(r['exact_message'] for r in valid),complete=complete))
    return dict(complete=all(r['complete'] for r in cells),cells=cells,
                writer_method=next(iter(writers)) if writers else None,
                scope='Reader ablations only; fixed-target writer ablation must be measured separately')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--subsets',type=Path,default=Path('configs/paper_subsets.json'))
    p.add_argument('--index',type=Path,required=True,help='JSON mapping sample IDs to ablation output directories')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();subset_data=a.subsets.read_bytes();index_data=a.index.read_bytes()
    expected=json.loads(subset_data)['ablation_i2v_30']
    index=json.loads(index_data);rows=[];evidence=[]
    if set(index)-set(expected):raise ValueError('Index includes samples outside frozen subset')
    for video_id,folder in index.items():
        folder=Path(folder)
        if not folder.is_absolute():folder=a.index.parent/folder
        for condition in CONDITIONS:
            for variant in VARIANTS:
                path=folder/f'{condition}-{variant}.json'
                if not path.exists():continue
                data=path.read_bytes()
                row=json.loads(data)
                if (row['video_id'],row['condition'],row['variant'])!=(video_id,condition,variant):raise ValueError('Receipt identity mismatch')
                rows.append(row);evidence.append(dict(video_id=video_id,condition=condition,variant=variant,sha256=hashlib.sha256(data).hexdigest()))
    result=summarize(rows,expected)
    result.update(receipts=evidence,index_sha256=hashlib.sha256(index_data).hexdigest(),subsets_sha256=hashlib.sha256(subset_data).hexdigest())
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'summary.json').write_text(json.dumps(result,indent=2))
    with (a.output/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(result['cells'][0]));writer.writeheader();writer.writerows(result['cells'])
    print(json.dumps(dict(complete=result['complete'],completed=sum(c['completed'] for c in result['cells']),expected=28*len(expected))))


if __name__=='__main__':main()
