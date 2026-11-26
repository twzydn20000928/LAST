"""Render audited aggregate counts as a Table2-style table without hiding coverage."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from .report import CONDITIONS


def verify_observations(report):
    by_cell = {}
    fields = ('family', 'mode', 'method', 'condition')
    for row in report['audited_observations']:
        videos = by_cell.setdefault(tuple(row[k] for k in fields), {})
        bits = row['correct_bits']
        if (row['video_id'] in videos or row['status'] != 'completed' or row['map_seed'] != 0
                or type(bits) is not int or not 0 <= bits <= 512 or row['total_bits'] != 512
                or row['exact_message'] is not (bits == 512)):
            raise ValueError('Invalid or duplicated primary observation')
        videos[row['video_id']] = bits
    for cell in report['cells']:
        bits = by_cell.pop(tuple(cell[k] for k in fields), {}).values()
        counts = (len(bits), sum(bits), 512 * len(bits), sum(n == 512 for n in bits))
        if counts != tuple(cell[k] for k in ('completed', 'correct_bits', 'total_bits', 'exact_messages')):
            raise ValueError('Cell counts differ from individual observations')
    if by_cell:
        raise ValueError('Observed condition missing from report cells')


def collect(reports):
    groups={}
    for report in reports:
        if report.get('artifact_verification') is not True:raise ValueError('Require artifact-audited aggregate reports')
        if 'audited_observations' in report:
            verify_observations(report)
        for row in report['cells']:
            key=tuple(row[k] for k in ('family','mode','method'))
            condition=row['condition']
            if condition not in CONDITIONS:raise ValueError('Unknown condition')
            cells=groups.setdefault(key,{})
            if condition in cells:raise ValueError('Overlapping snapshots must not be double counted')
            expected,done,correct,total,exact=[row[k] for k in ('expected','completed','correct_bits','total_bits','exact_messages')]
            if any(type(v) is not int for v in (expected,done,correct,total,exact)) or not 0<=done<=expected or expected<=0:
                raise ValueError('Invalid coverage counts')
            if 'failed' in row and (type(row['failed']) is not int or not 0 <= row['failed'] <= expected - done):
                raise ValueError('Invalid failed video count')
            if total!=done*512 or not 0<=correct<=total or not 0<=exact<=done or exact*512>correct:
                raise ValueError('Invalid recovery counts')
            if total - correct < done - exact:
                raise ValueError('Each non-exact message must contain at least one incorrect bit')
            complete=done==expected
            if row['complete']!=complete:raise ValueError('Incorrect completion flag')
            score=correct/total if total else None
            if not complete and row.get('final_bit_accuracy') is not None:raise ValueError('Partial observations cannot carry a final score')
            if complete and (row.get('final_bit_accuracy') is None or not math.isclose(row['final_bit_accuracy'],score,abs_tol=1e-12)):
                raise ValueError('Final accuracy differs from actual counts')
            planned = report.get('planned_videos_per_method', report.get('planned_videos', expected))
            if 'planned_videos' in report and report['planned_videos'] != planned:
                raise ValueError('Conflicting planned video counts')
            if type(planned) is not int or planned < expected:
                raise ValueError('Benchmark plan cannot be smaller than the audited subset')
            cells[condition] = dict(row, expected=planned, complete=done == planned,
                                    observed_bit_accuracy=score,
                                    final_bit_accuracy=score if done == planned else None)
    if not groups:raise ValueError('No aggregate cells')
    for cells in groups.values():
        if set(cells)!=set(CONDITIONS) or len({r['expected'] for r in cells.values()})!=1:
            raise ValueError('Require seven conditions with a common planned denominator per pipeline')
    return groups


def render(groups):
    labels=('Family','Mode','Method',*CONDITIONS)
    rows=[];coverage=[]
    for key,cells in sorted(groups.items()):
        values=[]
        for condition in CONDITIONS:
            r=cells[condition];score=r['observed_bit_accuracy']
            value='pending' if score is None else f'{100*r["correct_bits"]/r["total_bits"]:.2f}%'
            failed = r.get('failed')
            if failed and score is None:
                value = 'unscored'
            if not r['complete']:value+=' [partial]'
            values.append(f'{value}; {r["completed"]}/{r["expected"]}')
            if failed:
                values[-1] += f" ({failed} failed)"
            coverage.append(dict(family=key[0],mode=key[1],method=key[2],condition=condition,
                completed=r['completed'],expected=r['expected'],failed=failed,correct_bits=r['correct_bits'],total_bits=r['total_bits'],
                exact_messages=r['exact_messages'],observed_bit_accuracy=score,final_bit_accuracy=r.get('final_bit_accuracy')))
        rows.append((*key,*values))
    text=['# Measured robustness: bit accuracy and coverage','',
          'Percentages are recomputed from correct information bits. Each cell also shows completed/planned videos.',
          'Partial results are not final paper scores. No ranking or winner highlighting is applied.','',
          '| '+' | '.join(labels)+' |','|'+'|'.join(['---']*len(labels))+'|']
    text+=['| '+' | '.join(row)+' |' for row in rows]
    text+=['','Exact-message counts are retained separately in counts.csv; bit accuracy is not message recovery or authentication.',
           'This formatter consumes audited reports; it does not rerun their artifact audit or prove protocol comparability.']
    return '\n'.join(text)+'\n',coverage


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports',nargs='+',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();inputs={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.reports}
    groups=collect([json.loads(f.read_text(encoding='utf-8-sig')) for f in a.reports]);markdown,counts=render(groups)
    if any(hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h for f,h in inputs.items()):raise ValueError('Report changed')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'table.md').write_text(markdown,encoding='utf-8')
    with (a.output/'counts.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(counts[0]));writer.writeheader();writer.writerows(counts)
    receipt=dict(status='completed_rendering',supplied_cells_complete=all(r['complete'] for g in groups.values() for r in g.values()),
                 input_sha256=inputs,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 scope='Formatting only; no new measurements or comparability validation')
    (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


if __name__=='__main__':main()
