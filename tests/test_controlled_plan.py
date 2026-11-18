import json
from pathlib import Path
from copy import deepcopy
import pytest
from last.controlled_plan import make_plan
from last.lfg_calibration_report import select


def inputs():
    primary=json.loads((Path(__file__).parents[1]/'configs/primary_manifest.json').read_text())
    cells=[dict(candidate=f'{s}-{a}',lfg_final_steps=s,lfg_alpha=a,complete=True,expected=80,completed=80,missing=[],
                final_mean_video_psnr_db=33.1 if (s,a)==(5,.025) else 40.,final_mean_ssim=.96)
           for s in (5,10,20) for a in (.025,.05,.1,.15,.2)]
    return primary,dict(cells=cells,**select(cells))


def test_plan_keeps_every_primary_case_and_fixed_last_settings():
    primary,cal=inputs();plan=make_plan(primary,'sha',cal,'hunyuan')
    assert len(plan['runs'])==800 and len(plan['readers'])==4 and len(plan['conditions'])==3
    for writer in ('last','lfg-c'):
        rows=[r for r in plan['runs'] if r['method']==writer]
        assert [r['video_id'] for r in rows]==[s['id'] for s in primary['samples']]
    assert plan['runs'][0]['settings']==dict(margin=.5,fixed_target=False,uniform_profile=False)
    assert plan['runs'][400]['settings']==dict(lfg_alpha=.025,lfg_final_steps=5)


def test_incomplete_or_changed_selection_is_rejected():
    primary,cal=inputs()
    partial=deepcopy(cal);partial['cells'][-1]['completed']=79
    with pytest.raises(ValueError):make_plan(primary,'sha',partial,'hunyuan')
    changed=deepcopy(cal);changed['selected']['lfg_alpha']=.2
    with pytest.raises(ValueError):make_plan(primary,'sha',changed,'hunyuan')
    with pytest.raises(ValueError):make_plan(primary,'sha',dict(status='unmatched',selected=None),'hunyuan')
