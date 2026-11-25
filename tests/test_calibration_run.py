import json
from pathlib import Path
import pytest
from last.calibration_run import conditioning_case,sha,validate_plan
from last.lfg_calibration import make_plan


def test_grid_cannot_be_shortened_or_retuned():
    root=Path(__file__).resolve().parents[1]
    dev=json.loads((root/'configs/development_manifest.json').read_text())
    primary=json.loads((root/'configs/primary_manifest.json').read_text())
    plan=make_plan(dev,primary,'lfg-c','hunyuan')
    validate_plan(plan,dev,primary)
    plan['runs']=plan['runs'][:-1]
    with pytest.raises(ValueError):validate_plan(plan,dev,primary)


def test_conditioning_is_shared_across_seeds_and_hash_checked(tmp_path):
    rows=[dict(index=i,id=f'dev-{i:03}',prompt='fixed prompt',seed=100+i,key_slot=i) for i in range(4)]
    dev={'samples':rows}
    assert conditioning_case(rows[3],dev,tmp_path) is None
    folder=tmp_path/'prompt-00';folder.mkdir();(folder/'input.png').write_bytes(b'fixed conditioning')
    receipt=dict(status='completed',prompt='fixed prompt',seed=100,image_sha256=sha(folder/'input.png'))
    (folder/'receipt.json').write_text(json.dumps(receipt))
    case=conditioning_case(rows[3],dev,tmp_path)
    assert case['seed']==103 and case['image']==str(folder/'input.png')
    (folder/'input.png').write_bytes(b'changed')
    with pytest.raises(ValueError):conditioning_case(rows[3],dev,tmp_path)

@pytest.mark.parametrize("status,quality_exists", [("failed", True), ("running", False), ("completed", False)])
def test_restart_preserves_interrupted_run(tmp_path, monkeypatch, status, quality_exists):
    import sys
    from last.calibration_run import main

    # Exercise the Linux locking path without launching a writer or requiring a GPU.
    pytest.importorskip("fcntl")
    repo = Path(__file__).resolve().parents[1]
    dev_path = repo / "configs/development_manifest.json"
    primary_path = repo / "configs/primary_manifest.json"
    dev = json.loads(dev_path.read_bytes())
    plan = make_plan(dev, json.loads(primary_path.read_bytes()), "lfg-c", "hunyuan")
    plan["manifest_sha256"] = {"development": sha(dev_path), "primary": sha(primary_path)}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    (tmp_path / "state.json").write_text(json.dumps({"manifest_sha256": sha(dev_path)}))
    prompt = tmp_path / "prompt-00"
    prompt.mkdir()
    (prompt / "input.png").write_bytes(b"conditioning")
    sample = dev["samples"][0]
    (prompt / "receipt.json").write_text(json.dumps(dict(
        status="completed", prompt=sample["prompt"], seed=sample["seed"],
        image_sha256=sha(prompt / "input.png"))))
    item = plan["runs"][0]
    folder = tmp_path / item["run"]
    folder.mkdir(parents=True)
    receipt = folder / "calibration.json"
    receipt.write_text(json.dumps(dict(status=status, item=item)))
    before = receipt.read_bytes()
    if quality_exists:
        (folder / "quality.json").write_text("{}")
    monkeypatch.setattr(sys, "argv", ["calibration_run", "--plan", str(plan_path),
        "--development", str(dev_path), "--primary", str(primary_path), "--root", str(tmp_path),
        "--state", str(tmp_path), "--conditioning", str(tmp_path), "--model-dir", str(tmp_path),
        "--writer-root", str(repo)])
    monkeypatch.setattr("os.umask", lambda mask: 0)
    with pytest.raises(ValueError, match="calibration run"):
        main()
    assert receipt.read_bytes() == before
