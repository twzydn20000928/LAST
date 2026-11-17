"""Freeze the supplement's development-only LFG strength/step grid.

This creates a plan, not a fitted parameter or a completed experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .development import validate_development

STRENGTHS = (.025, .05, .10, .15, .20)
STEPS = (5, 10, 20)


def make_plan(development, primary, method, family):
    validate_development(development, primary)
    if method not in ('lfg', 'lfg-c') or family not in ('hunyuan', 'wan22'):
        raise ValueError('Unsupported calibration writer/backbone')
    runs = []
    for steps in STEPS:
        for strength in STRENGTHS:
            candidate = f'alpha-{strength:.3f}-steps-{steps:02}'
            for sample in development['samples']:
                runs.append(dict(candidate=candidate, video_id=sample['id'],
                                 index=sample['index'], key_slot=sample['key_slot'],
                                 seed=sample['seed'], family=family, mode='i2v', method=method,
                                 lfg_alpha=strength, lfg_final_steps=steps,
                                 run=f'{family}/i2v/{method}/{candidate}/{sample["id"]}'))
    return dict(schema_version=1, scope='Supplement development calibration; no primary-test outcomes',
                source='Updated supplement: final 5/10/20 steps and strengths .025/.05/.10/.15/.20',
                samples_per_candidate=80, candidates=15, runs=runs,
                fidelity_target=dict(mean_video_psnr_db=33.1, tolerance_db=.1, mean_ssim_min=.950),
                selection=dict(requires_complete_grid=True, accuracy_not_used=True,
                               ordering=['absolute distance of mean per-video PSNR to 33.1',
                                         'fewer guided steps', 'smaller strength'],
                               no_eligible_candidate='Unmatched; no selected operating point'),
                pending='Generation, quality evaluation, verification and parameter freeze are not completed by this plan')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', type=Path, default=Path('configs/development_manifest.json'))
    parser.add_argument('--primary', type=Path, default=Path('configs/primary_manifest.json'))
    parser.add_argument('--method', choices=['lfg', 'lfg-c'], required=True)
    parser.add_argument('--family', choices=['hunyuan', 'wan22'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = make_plan(json.loads(args.development.read_text()), json.loads(args.primary.read_text()), args.method, args.family)
    plan['manifest_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for name, path in [('development', args.development), ('primary', args.primary)]}
    plan['planner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(plan, stream, indent=2)
    print(json.dumps(dict(runs=len(plan['runs']), candidates=15, calibrated=False)))


if __name__ == '__main__':
    main()
