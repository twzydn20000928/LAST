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
        if 'coded_correct' in row or 'coded_total' in row:
            coded = row.get('coded_correct')
            if row.get('coded_total') != 592 or type(coded) is not int or not 0 <= coded <= 592:
                raise ValueError('Invalid 592-bit codeword count')
            if pre is not None and not 0 <= coded - pre <= 80:
                raise ValueError('Codeword and systematic information counts disagree')
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
    coded_rows = [r for r in valid if 'coded_correct' in r]
    coded_bits = 592 * len(coded_rows)
    coded_errors = sum(592 - r['coded_correct'] for r in coded_rows)
    return dict(expected=len(expected_ids),completed=count,complete=complete,incomplete_ids=incomplete,
                coded_observations=len(coded_rows), coded_total_bits=coded_bits, coded_error_bits=coded_errors,
                observed_coded_ber=coded_errors / coded_bits if coded_bits else None,
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


def render_tables(result):
    def value(n):
        return '—' if n is None else f'{n:.3f}'

    identity = ' / '.join(result[k] for k in ('family','mode','method'))
    first = [f'# Message outcomes — {identity}, map {result["map_seed"]}', '',
             'Each row gives the observed sample count and planned denominator.', '',
             '| Attack | Coverage | Pre-BCH bit accuracy | Post-BCH bit accuracy | Exact | Rejected wrong | Miscorrected | MRR Wilson 95% CI |',
             '|---|---:|---:|---:|---:|---:|---:|---|']
    second = ['| Attack | Coverage | Errors pre | Errors post | BER median | BER P95 | BER P99 | BER max |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for condition in CONDITIONS:
        row = result['conditions'][condition]
        n = row['completed']
        coverage = f"{n}/{row['expected']}"
        errors = row['pre_bch_error_bits']
        pre = 1 - errors / (512*n) if n and errors is not None else None
        interval = row['observed_mrr_wilson95']
        ci = '—' if interval is None else f'[{interval[0]:.3f}, {interval[1]:.3f}]'
        first.append('| ' + ' | '.join([condition, coverage, value(pre), value(row['observed_bit_accuracy']),
                     f"{row['exact_messages']}/{n}" if n else '—',
                     str(row['wrong_decoder_failure']) if n else '—',
                     str(row['wrong_decoder_success']) if n else '—', ci]) + ' |')
        counts = [str(errors) if errors is not None else '—', str(row['post_bch_error_bits']) if n else '—']
        quantiles = [value(row['post_bch_ber_quantiles'][q]) for q in ('median','p95','p99','max')]
        second.append('| ' + ' | '.join([condition, coverage, *counts, *quantiles]) + ' |')
    return '\n'.join(first + ['', *second, ''])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family',choices=['hunyuan','wan22'],required=True);p.add_argument('--mode',choices=['i2v','t2v'],required=True)
    p.add_argument('--method',choices=['last','lfg','lfg-c'],required=True)
    p.add_argument('--map-seed',type=int,choices=range(5),default=0)
    p.add_argument('--markdown',type=Path,help='Also render the message recovery and error quantile tables')
    p.add_argument('--reextraction-index',type=Path,help='Verified primary LAST replay runs for this pipeline')
    a=p.parse_args()
    if a.markdown and a.markdown.resolve()==a.output.resolve():
        p.error('Choose distinct JSON and Markdown outputs')
    manifest=json.loads(a.manifest.read_text());ids=[r['id'] for r in manifest['samples']];root=a.root.resolve()
    result=dict(family=a.family,mode=a.mode,method=a.method,map_seed=a.map_seed,
                manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),conditions={},receipt_sha256={})
    replays = {}
    if a.reextraction_index:
        from .reextract_evidence import verified_rows
        if a.map_seed != 0 or a.method != 'last':
            p.error('The replay index applies to primary-map LAST observations')
        planned = {f'{a.family}/{a.mode}/{a.method}/{identity}': identity for identity in ids}
        index_bytes = a.reextraction_index.read_bytes()
        for entry in json.loads(index_bytes):
            run = entry['run']
            if run not in planned or planned[run] in replays:
                raise ValueError('Unexpected or duplicate replay run')
            folder = (root/run).resolve()
            if not folder.is_relative_to(root):
                raise ValueError('Unsafe replay path')
            replays[planned[run]] = verified_rows(folder, entry['output'], entry['source'])
        result['reextraction_index_sha256'] = hashlib.sha256(index_bytes).hexdigest()
        result['reextraction_receipt_sha256'] = {
            identity: next(iter(rows.values()))['reextraction_receipt_sha256'] for identity, rows in replays.items()}
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
                if condition in replays.get(identity, {}):
                    # Historical pre-decoding decisions belong to the original pass.
                    row.pop('raw_information_correct', None)
                    row.pop('coded_correct', None)
                    row.pop('coded_total', None)
                    row.update(replays[identity][condition])
                rows.append(row);result['receipt_sha256'][str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        result['conditions'][condition]=summarize(rows,ids)
    result['complete']=all(r['complete'] for r in result['conditions'].values())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    if a.markdown:
        a.markdown.parent.mkdir(parents=True,exist_ok=True)
        a.markdown.write_text(render_tables(result),encoding='utf-8')
    print(json.dumps(dict(complete=result['complete'],completed={k:v['completed'] for k,v in result['conditions'].items()})))


if __name__=='__main__':main()
