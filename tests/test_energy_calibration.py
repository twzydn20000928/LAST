import copy
import json
from pathlib import Path
import numpy as np
import pytest
from last.energy_calibration import fit,transform,projected_energy


def manifests():
    root=Path(__file__).resolve().parents[1]/'configs'
    return (json.loads((root/'development_manifest.json').read_text()),
            json.loads((root/'primary_manifest.json').read_text()))


def test_group_bias_removed_and_test_input_cannot_refit():
    dev,primary=manifests();ids=[r['id'] for r in dev['samples']]
    base=np.tile(np.linspace(1,3,64)[None,:,None],(80,1,16))
    offsets=np.arange(16)*10
    calibration=fit(base+offsets,ids,dev,primary)
    frozen=copy.deepcopy(calibration)
    assert np.allclose(transform(2+offsets,calibration),0)
    assert np.allclose(transform(3+offsets,calibration),np.repeat(1/calibration['scale'][0],16))
    transform(np.ones((7,16))*100,calibration)
    assert calibration==frozen


def test_development_coverage_and_null_count_enforced():
    dev,primary=manifests();ids=[r['id'] for r in dev['samples']]
    energy=np.ones((80,64,16))
    with pytest.raises(ValueError,match='all80'):fit(energy[:-1],ids[:-1],dev,primary)
    with pytest.raises(ValueError,match='all80'):fit(energy,['paper-000']+ids[1:],dev,primary)
    with pytest.raises(ValueError,match='x64x16'):fit(energy[:,:63],ids,dev,primary)
    calibration=fit(energy,ids,dev,primary)
    assert calibration['degenerate_groups']==list(range(16))
    assert np.isfinite(transform(np.ones((2,16)),calibration)).all()


def test_energy_statistic_and_invalid_inputs():
    values=np.ones((3,16,592));values[...,::2]=-1
    assert np.array_equal(projected_energy(values),np.ones((3,16)))
    values[0,0,0]=np.nan
    with pytest.raises(ValueError):projected_energy(values)
    with pytest.raises(ValueError):projected_energy(np.ones((16,512)))
