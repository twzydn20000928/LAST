"""A Table 12 comparison must use the same fitted reader across videos."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from controlled_reader_table import render


def test_calibrated_table_requires_common_fit(tmp_path):
    paths = []
    for sample in ("005", "006"):
        name = f"hunyuan_i2v_last_controlled_paper{sample}.json"
        case = json.loads((ROOT / "results" / name).read_bytes())
        # Construct a schema fixture from measured counts, without claiming calibrated measurements.
        case["rows"] += [dict(row, reader="calibrated_energy") for row in case["rows"] if row["reader"] == "ccta"]
        case.update(complete_reader_set=True, calibration_sha256="a" * 64)
        path = tmp_path / name
        path.write_text(json.dumps(case))
        paths.append(path)
    manifest = ROOT / "configs/primary_manifest.json"
    assert "calibrated_energy" in render(paths, manifest)
    case["calibration_sha256"] = "b" * 64
    paths[-1].write_text(json.dumps(case))
    with pytest.raises(ValueError, match="calibrations"):
        render(paths, manifest)
    del case["calibration_sha256"]
    paths[-1].write_text(json.dumps(case))
    with pytest.raises(ValueError, match="Missing calibration fingerprint"):
        render(paths, manifest)
