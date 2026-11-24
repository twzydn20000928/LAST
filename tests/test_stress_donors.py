import hashlib
import json
from pathlib import Path

import pytest

from last.stress_donors import plan, resolve


CONFIG = Path(__file__).resolve().parents[1] / "configs"
MANIFEST = CONFIG / "primary_manifest.json"
DONORS = CONFIG / "stress_donors.json"


def test_registered_donors_are_reproducible_and_different_prompt():
    frozen = json.loads(DONORS.read_bytes())
    assert frozen == plan(MANIFEST)
    prompts = {r["id"]: " ".join(r["prompt"].casefold().split())
               for r in json.loads(MANIFEST.read_bytes())["samples"]}
    pairs = frozen["assignments"]
    assert set(pairs) == set(pairs.values()) == set(prompts)
    assert all(prompts[target] != prompts[donor] for target, donor in pairs.items())


def test_resolve_checks_reference_against_assigned_case(tmp_path):
    donor = tmp_path / "paper-020"
    donor.mkdir()
    sample = json.loads(MANIFEST.read_bytes())["samples"][20]
    case = json.dumps(dict(video_id=sample["id"], seed=sample["seed"], prompt=sample["prompt"])).encode()
    (donor / "case.json").write_bytes(case)
    (donor / "receipt.json").write_text(json.dumps(dict(status="completed", method="last",
        case_sha256=hashlib.sha256(case).hexdigest(), marked_sha256="marked")))
    ref = donor / "reference.mp4"
    ref.write_bytes(b"reference fixture")
    (donor / "quality.json").write_text(json.dumps(dict(marked_sha256="marked",
        reference_sha256=hashlib.sha256(ref.read_bytes()).hexdigest())))
    assert resolve(DONORS, MANIFEST, tmp_path, "paper-000") == (ref, "paper-020")
    ref.write_bytes(b"changed")
    with pytest.raises(ValueError, match="reference differs"):
        resolve(DONORS, MANIFEST, tmp_path, "paper-000")
