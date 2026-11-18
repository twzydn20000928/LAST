"""Freeze Table12 shared-carrier cases only after full development calibration."""
import argparse,json
from pathlib import Path
from .campaign import digest,source_digest
from .data import validate
from .lfg_calibration_report import report,select
from .controlled_evaluate import READERS,CONDITIONS


def make_plan(primary,primary_sha,calibration,family):
    validate(primary)
    if family not in ('hunyuan','wan22'):raise ValueError('Unsupported family')
    if calibration.get('status')!='calibrated' or calibration.get('selected') is None:
        raise ValueError('Full development grid has not selected a matched-fidelity LFG-C operating point')
    if any(c.get('completed')!=80 or c.get('expected')!=80 or c.get('missing') for c in calibration['cells']):
        raise ValueError('Require all80 samples in every calibration cell')
    if select(calibration['cells'])!={k:calibration[k] for k in ('status','selected')}:
        raise ValueError('Calibration selection differs from fidelity-only rule')
    selected=calibration['selected'];runs=[]
    for method in ('last','lfg-c'):
        for sample in primary['samples']:
            settings=dict(margin=.5,fixed_target=False,uniform_profile=False) if method=='last' else dict(
                lfg_alpha=selected['lfg_alpha'],lfg_final_steps=selected['lfg_final_steps'])
            runs.append(dict(family=family,mode='i2v',method=method,video_id=sample['id'],index=sample['index'],
                             key_slot=sample['key_slot'],seed=sample['seed'],settings=settings,
                             run=f'{family}/i2v/{method}/{sample["id"]}'))
    return dict(schema_version=1,scope='Table12 shared-carrier block: two writers x400 I2V cases; native LFG rows separate',
                manifest_sha256=primary_sha,source_sha256=source_digest(),readers=list(READERS),conditions=list(CONDITIONS),
                selected_lfg_c=selected,runs=runs,
                pending='Plan only: matched-writer generation, frozen energy fit, reader execution and aggregation remain separate')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('primary','development','calibration-plan','calibration-root','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    primary=json.loads(a.primary.read_text());development=json.loads(a.development.read_text())
    grid=json.loads(a.calibration_plan.read_text());first=grid['runs'][0]
    if first['method']!='lfg-c':raise ValueError('Require shared-carrier LFG-C calibration, not native LFG')
    for name,path in (('primary',a.primary),('development',a.development)):
        if digest(path)!=grid['manifest_sha256'][name]:raise ValueError('Calibration manifest changed')
    # Recheck actual calibration videos and receipts, not a supplied success flag.
    calibration=report(grid,development,primary,a.calibration_root)
    result=make_plan(primary,digest(a.primary),calibration,first['family'])
    result['calibration_plan_sha256']=digest(a.calibration_plan)
    result['calibration_evidence']=calibration['evidence']
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(writer_cases=len(result['runs']),readouts=len(result['runs'])*len(READERS)*len(CONDITIONS),executed=False)))


if __name__=='__main__':main()
