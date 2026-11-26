"""Aggregate an explicit experiment plan; incomplete cells never become final scores."""
import argparse,csv,json,hashlib
from collections import defaultdict
from pathlib import Path
CONDITIONS=('clean','noise','compression','blur','drop','insert','clip')

def aggregate(plan,root,verify_artifacts=False,reextractions=None,*,native_retry_dirs=None):
    cells=defaultdict(list);seen=set();diagnostics=[]
    root=Path(root).resolve();audited=[]
    reextractions=reextractions or {}
    if reextractions and not verify_artifacts:raise ValueError('Re-extraction reuse requires artifact verification')
    if set(reextractions)-{i['run'] for i in plan['runs']}:raise ValueError('Re-extraction index contains unplanned runs')
    retries = dict(native_retry_dirs or {})
    if retries and (not verify_artifacts or reextractions):
        raise ValueError("Native retries require verification in a separate report from re-extractions")
    for item in plan['runs']:
        identity=(item['family'],item['mode'],item['method'],item['video_id'])
        if identity in seen:raise ValueError('Duplicate planned observation')
        seen.add(identity)
        folder=(root/item['run']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Planned run escapes result root')
        marked_sha=None
        replacement={}
        if item['run'] in reextractions:
            from .reextract_evidence import verified_rows
            entry=reextractions[item['run']]
            replacement=verified_rows(folder,entry['output'],entry['source'])
        for condition in CONDITIONS:
            path=folder/'attacks'/(condition+'.json');state='missing';row=None
            original_hash = None
            retry = retries.pop((item['run'], condition), None)
            if retry is not None:
                original_bytes = path.read_bytes()
                original_hash = hashlib.sha256(original_bytes).hexdigest()
                original = json.loads(original_bytes)
                path = Path(retry) / (condition + '.json')
                if not path.is_file():
                    raise ValueError('Native retry receipt missing')
            if path.exists():
                receipt_bytes = path.read_bytes()
                row=json.loads(receipt_bytes);state=row['status']
                if retry is not None:
                    fields = ('condition', 'video_id', 'method', 'map_seed', 'source_sha256',
                              'state_sha256', 'received_sha256', 'attack_map')
                    if (original['status'] != 'failed' or state != 'completed'
                            or row.get('retry_of_sha256') != original_hash
                            or any(original[k] != row[k] for k in fields)):
                        raise ValueError('Native retry differs from original failed input')
                if row.get('map_seed', 0) != 0:
                    raise ValueError(f'Expected map seed 0 in the primary attacks directory: {path}')
                if row.get('video_id')!=item['video_id'] or row.get('condition')!=condition:raise ValueError(f'Receipt identity mismatch:{path}')
                if row.get('method',item['method'])!=item['method']:raise ValueError(f'Method mismatch:{path}')
                if condition in replacement:
                    row=dict(row,**replacement[condition]);state=row['status']
                if state=='completed':
                    total=row['total_bits'];correct=row['correct_bits']
                    if type(total)!=int or total!=512 or type(correct)!=int or not 0<=correct<=total:raise ValueError('Invalid bit counts')
                    if row['exact_message']!=(correct==total):raise ValueError('Inconsistent exact-message count')
                    if verify_artifacts:
                        if marked_sha is None:
                            marked_sha=hashlib.sha256((folder/'marked.mp4').read_bytes()).hexdigest()
                            generation=json.loads((folder/'receipt.json').read_text())
                            if generation.get('status') not in ('completed','completed_generation_only'):raise ValueError('Source generation incomplete')
                            for field in ('marked_sha256', 'video_sha256'):
                                if field in generation and generation[field] != marked_sha:
                                    raise ValueError(f'Generated MP4 differs from generation receipt: {folder}')
                            for field in ('family','mode','method'):
                                if generation.get(field)!=item[field]:raise ValueError(f'Generation {field} mismatch')
                        if row.get('source_sha256')!=marked_sha:raise ValueError('Attack receipt refers to a different source video')
                        attacked=folder/'marked.mp4' if condition=='clean' else folder/'attacks'/(condition+'.mp4')
                        if not attacked.is_file():raise ValueError('Completed attack video missing')
                        received_sha=hashlib.sha256(attacked.read_bytes()).hexdigest()
                        recorded_received=row.get('received_sha256',row.get('source_sha256') if condition=='clean' else None)
                        if recorded_received!=received_sha:raise ValueError(f'Attack receipt received-video hash missing or mismatched: {path}')
                        evidence = dict(family=item['family'], mode=item['mode'], method=item['method'],
                                        video_id=item['video_id'], run=item['run'], condition=condition,
                                        map_seed=0, status=state, correct_bits=correct, total_bits=total,
                                        exact_message=(correct == total), video_sha256=received_sha,
                                        receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest())
                        if original_hash is not None:
                            evidence['retry_of_sha256'] = original_hash
                        if condition in replacement:
                            evidence.update({k:v for k,v in replacement[condition].items() if k.startswith('reextraction_')})
                            evidence.update(prior_correct_bits=row['prior_correct_bits'],same_correct_bit_count=row['same_correct_bit_count'])
                        audited.append(evidence)
            cells[identity[:3]+(condition,)].append((state,row))
            if state!='completed':diagnostics.append(dict(family=identity[0],mode=identity[1],method=identity[2],video_id=identity[3],condition=condition,status=state))
    if retries:
        raise ValueError('Native retry references a condition outside the plan')
    output=[]
    for (family,mode,method,condition),observations in sorted(cells.items()):
        valid=[r for status,r in observations if status=='completed'];count=len(valid);complete=count==len(observations)
        correct=sum(r['correct_bits'] for r in valid);bits=sum(r['total_bits'] for r in valid)
        exact=sum(r['exact_message'] for r in valid)
        output.append(dict(family=family,mode=mode,method=method,condition=condition,expected=len(observations),completed=count,missing=sum(s=='missing' for s,r in observations),failed=sum(s=='failed' for s,r in observations),correct_bits=correct,total_bits=bits,observed_bit_accuracy=correct/bits if bits else None,final_bit_accuracy=correct/bits if bits and complete else None,exact_messages=exact,observed_message_recovery=exact/count if count else None,complete=complete))
    return dict(scope=plan['scope'],complete=bool(output) and not diagnostics,cells=output,incomplete_observations=diagnostics,artifact_verification=verify_artifacts,audited_observations=audited)

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify-artifacts',action='store_true');p.add_argument('--reextraction-index',type=Path);a=p.parse_args()
    index={}
    if a.reextraction_index:
        for entry in json.loads(a.reextraction_index.read_text()):
            if entry['run'] in index:raise ValueError('Duplicate re-extraction index run')
            index[entry['run']]=entry
    report=aggregate(json.loads(a.plan.read_text()),a.root,a.verify_artifacts,index);report['plan_sha256']=hashlib.sha256(a.plan.read_bytes()).hexdigest();a.output.mkdir(parents=True,exist_ok=True)
    if a.reextraction_index:report['reextraction_index_sha256']=hashlib.sha256(a.reextraction_index.read_bytes()).hexdigest()
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
