"""Aggregate an explicit experiment plan; incomplete cells never become final scores."""
import argparse,csv,json,hashlib
from collections import defaultdict
from pathlib import Path
CONDITIONS=('clean','noise','compression','blur','drop','insert','clip')

def aggregate(plan,root,verify_artifacts=False):
    cells=defaultdict(list);seen=set();diagnostics=[]
    root=Path(root).resolve();audited=[]
    for item in plan['runs']:
        identity=(item['family'],item['mode'],item['method'],item['video_id'])
        if identity in seen:raise ValueError('Duplicate planned observation')
        seen.add(identity)
        folder=(root/item['run']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Planned run escapes result root')
        marked_sha=None
        for condition in CONDITIONS:
            path=folder/'attacks'/(condition+'.json');state='missing';row=None
            if path.exists():
                row=json.loads(path.read_text());state=row['status']
                if row.get('video_id')!=item['video_id'] or row.get('condition')!=condition:raise ValueError(f'Receipt identity mismatch:{path}')
                if row.get('method',item['method'])!=item['method']:raise ValueError(f'Method mismatch:{path}')
                if state=='completed':
                    total=row['total_bits'];correct=row['correct_bits']
                    if type(total)!=int or total!=512 or type(correct)!=int or not 0<=correct<=total:raise ValueError('Invalid bit counts')
                    if row['exact_message']!=(correct==total):raise ValueError('Inconsistent exact-message count')
                    if verify_artifacts:
                        if marked_sha is None:
                            marked_sha=hashlib.sha256((folder/'marked.mp4').read_bytes()).hexdigest()
                            generation=json.loads((folder/'receipt.json').read_text())
                            if generation.get('status') not in ('completed','completed_generation_only'):raise ValueError('Source generation incomplete')
                            for field in ('family','mode','method'):
                                if generation.get(field)!=item[field]:raise ValueError(f'Generation {field} mismatch')
                        if row.get('source_sha256')!=marked_sha:raise ValueError('Attack receipt refers to a different source video')
                        attacked=folder/'marked.mp4' if condition=='clean' else folder/'attacks'/(condition+'.mp4')
                        if not attacked.is_file():raise ValueError('Completed attack video missing')
                        audited.append(dict(run=item['run'],condition=condition,receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),video_sha256=hashlib.sha256(attacked.read_bytes()).hexdigest()))
            cells[identity[:3]+(condition,)].append((state,row))
            if state!='completed':diagnostics.append(dict(family=identity[0],mode=identity[1],method=identity[2],video_id=identity[3],condition=condition,status=state))
    output=[]
    for (family,mode,method,condition),observations in sorted(cells.items()):
        valid=[r for status,r in observations if status=='completed'];count=len(valid);complete=count==len(observations)
        correct=sum(r['correct_bits'] for r in valid);bits=sum(r['total_bits'] for r in valid)
        exact=sum(r['exact_message'] for r in valid)
        output.append(dict(family=family,mode=mode,method=method,condition=condition,expected=len(observations),completed=count,missing=sum(s=='missing' for s,r in observations),failed=sum(s=='failed' for s,r in observations),correct_bits=correct,total_bits=bits,observed_bit_accuracy=correct/bits if bits else None,final_bit_accuracy=correct/bits if bits and complete else None,exact_messages=exact,observed_message_recovery=exact/count if count else None,complete=complete))
    return dict(scope=plan['scope'],complete=bool(output) and not diagnostics,cells=output,incomplete_observations=diagnostics,artifact_verification=verify_artifacts,audited_observations=audited)

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify-artifacts',action='store_true');a=p.parse_args()
    report=aggregate(json.loads(a.plan.read_text()),a.root,a.verify_artifacts);report['plan_sha256']=hashlib.sha256(a.plan.read_bytes()).hexdigest();a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'summary.json').write_text(json.dumps(report,indent=2))
    if report['cells']:
        with (a.output/'summary.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(report['cells'][0]));writer.writeheader();writer.writerows(report['cells'])
    lines=['# Measured results','',f"Scope: {report['scope']}",'','| Family | Mode | Method | Attack | Completed/expected | Bit accuracy | Exact messages |','|---|---|---|---|---|---|---|']
    for row in report['cells']:
        score=f"{row['observed_bit_accuracy']:.6f}" if row['observed_bit_accuracy'] is not None else '—'
        if not row['complete']:score+=' (partial)'
        lines.append(f"| {row['family']} | {row['mode']} | {row['method']} | {row['condition']} | {row['completed']}/{row['expected']} | {score} | {row['exact_messages']}/{row['completed']} |")
    lines+=['','Missing and failed observations remain explicit. Partial cells have no final score. Bit accuracy, exact-message recovery and authentication are distinct.']
    (a.output/'summary.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(complete=report['complete'],cells=len(report['cells']),incomplete=len(report['incomplete_observations']))))
if __name__=='__main__':main()
