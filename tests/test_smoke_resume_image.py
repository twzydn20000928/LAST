import hashlib
import json
import sys

import pytest

from last import smoke


def test_completed_image_run_detects_same_path_new_contents(tmp_path, monkeypatch):
    image = tmp_path / "condition.png"
    image.write_bytes(b"original conditioning bytes")
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"image": str(image)}))
    run = tmp_path / "run"
    run.mkdir()
    receipt = dict(status="completed", family="hunyuan", mode="i2v",
                   case_sha256=hashlib.sha256(case.read_bytes()).hexdigest(),
                   conditioning_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    (run / "marked.mp4").write_bytes(b"marked")
    (run / "reference.mp4").write_bytes(b"reference")
    receipt["marked_sha256"] = hashlib.sha256(b"marked").hexdigest()
    (run / "receipt.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(sys, "argv", ["last.smoke", "--case", str(case), "--output", str(run),
                                      "--family", "hunyuan", "--mode", "i2v", "--model-dir", str(tmp_path)])
    smoke.main()
    image.write_bytes(b"replacement conditioning bytes")
    with pytest.raises(ValueError, match="Conditioning image differs"):
        smoke.main()

    image.write_bytes(b"original conditioning bytes")
    (run / "marked.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError, match="unverified marked.mp4"):
        smoke.main()
    (run / "marked.mp4").write_bytes(b"marked")
    (run / "reference.mp4").unlink()
    with pytest.raises(ValueError, match="missing reference.mp4"):
        smoke.main()
