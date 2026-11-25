"""Verify the full development grid and select by fidelity, never bit accuracy."""
import argparse
import hashlib
import json
from pathlib import Path
from .fidelity_summary import summarize
from .lfg_calibration import make_plan


def select(cells):
    if len(cells) != 15 or not all(c['complete'] for c in cells):
        return dict(status='incomplete', selected=None)
    eligible = [c for c in cells if c['final_mean_video_psnr_db'] is not None
                and abs(c['final_mean_video_psnr_db'] - 33.1) <= .1 + 1e-10
                and c['final_mean_ssim'] >= .950]
    if not eligible:
        return dict(status='unmatched', selected=None)
    best = min(eligible, key=lambda c: (abs(c['final_mean_video_psnr_db'] - 33.1),
                                      c['lfg_final_steps'], c['lfg_alpha']))
    return dict(status='calibrated', selected={k: best[k] for k in
                ('candidate', 'lfg_alpha', 'lfg_final_steps', 'final_mean_video_psnr_db', 'final_mean_ssim')})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(plan, development, primary, root):
    first = plan['runs'][0]
    expected = make_plan(development, primary, first['method'], first['family'])
    for field in ('runs', 'fidelity_target', 'selection', 'samples_per_candidate', 'candidates'):
        if plan[field] != expected[field]:
            raise ValueError('Plan differs from frozen calibration protocol: ' + field)
    root = root.resolve()
    groups = {}; evidence = []; sources = set(); definitions = set()
    for item in plan['runs']:
        group = groups.setdefault(item['candidate'], dict(expected=[], rows=[], item=item))
        group['expected'].append(item['video_id'])
        folder = (root / item['run']).resolve()
        if not folder.is_relative_to(root):
            raise ValueError('Unsafe run path')
        quality = folder / 'quality.json'
        if not quality.exists():
            continue
        # The runner writes quality.json before its final input integrity check.
        # Earlier standalone calibration runs have no orchestration receipt.
        run_receipt = folder / 'calibration.json'
        if run_receipt.exists():
            run = json.loads(run_receipt.read_text())
            if run.get('status') == 'running':
                continue
            if run.get('status') != 'completed' or run.get('item') != item:
                raise ValueError(f'Calibration run did not complete as planned: {item["run"]}')
        receipt = folder / 'receipt.json'
        generation = json.loads(receipt.read_text())
        if generation.get('status') != 'completed' or any(generation.get(k) != item[k] for k in
                ('family', 'mode', 'method', 'seed', 'lfg_alpha', 'lfg_final_steps')):
            raise ValueError('Generation does not match calibration cell')
        source = generation.get('source_sha256')
        if not source:
            raise ValueError('Missing writer source provenance')
        sources.add(source)
        case_path = folder / 'case.json'
        case = json.loads(case_path.read_text())
        sample = development['samples'][item['index']]
        if sha(case_path) != generation.get('case_sha256') or any(
                case.get(k) != sample[k] for k in ('prompt', 'seed')):
            raise ValueError('Generation case differs from frozen development sample')
        row = json.loads(quality.read_text())
        for name in ('reference', 'marked'):
            if sha(folder / (name + '.mp4')) != row[name + '_sha256']:
                raise ValueError('Quality video checksum mismatch')
        if generation['marked_sha256'] != row['marked_sha256']:
            raise ValueError('Generation/quality video mismatch')
        definitions.add(row['definition'])
        group['rows'].append(dict(row, video_id=item['video_id']))
        evidence.append(dict(run=item['run'], generation_sha256=sha(receipt), quality_sha256=sha(quality)))
    if len(sources) > 1 or len(definitions) > 1:
        raise ValueError('Mixed writer versions or fidelity definitions require a separate audit')
    cells = []
    for candidate, group in groups.items():
        item = group['item']
        cells.append(dict(candidate=candidate, lfg_alpha=item['lfg_alpha'],
                          lfg_final_steps=item['lfg_final_steps'], **summarize(group['rows'], group['expected'])))
    return dict(scope='Development-only fidelity calibration; no robustness ranking or V-score',
                **select(cells), cells=cells, evidence=evidence, writer_source_sha256=sorted(sources))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--development', type=Path, default=Path('configs/development_manifest.json'))
    parser.add_argument('--primary', type=Path, default=Path('configs/primary_manifest.json'))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    for name, path in [('development', args.development), ('primary', args.primary)]:
        if sha(path) != plan['manifest_sha256'][name]:
            raise ValueError('Manifest checksum mismatch')
    result = report(plan, json.loads(args.development.read_text()), json.loads(args.primary.read_text()), args.root)
    result['plan_sha256'] = sha(args.plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result['status'], selected=result['selected'],
                          completed=sum(c['completed'] for c in result['cells']), expected=1200)))


if __name__ == '__main__':
    main()
