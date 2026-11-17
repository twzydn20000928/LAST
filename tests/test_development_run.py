import copy,json
from pathlib import Path
import pytest
from last.development_run import make_plan,validate_plan


def test_frozen_development_cannot_be_shortened_or_retuned():
    root=Path(__file__).resolve().parents[1]
    dev=json.loads((root/'configs/development_manifest.json').read_text())
    primary=json.loads((root/'configs/primary_manifest.json').read_text())
    plan=make_plan(dev,primary,'hunyuan');validate_plan(plan,dev,primary)
    assert len(plan['samples'])==80
    for field,value in [('samples',plan['samples'][:-1]),('mu',1.),('uniform_profile',True),('source_sha256','changed')]:
        bad=copy.deepcopy(plan);bad[field]=value
        with pytest.raises(ValueError):validate_plan(bad,dev,primary)
