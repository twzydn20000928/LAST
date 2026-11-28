"""Replay the public demo edits on CPU and compare them to the published MP4s."""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("cv2")
pytest.importorskip("imageio_ffmpeg")
pytest.importorskip("PIL")
pytestmark = pytest.mark.skipif(
    (sys.platform, platform.machine()) != ("linux", "x86_64"),
    reason="Published MP4 digests use the pinned Linux x86-64 encoder",
)

from last.video import load_mp4


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/public_demo/sailboat.mp4"
REPORT = json.loads((ROOT / "results/public_sailboat_attacks.json").read_bytes())


@pytest.mark.parametrize("condition", ["noise", "compression", "blur", "drop", "insert", "clip"])
def test_replay_published_edit(condition, tmp_path):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == REPORT["source_sha256"]
    out = tmp_path / "received.mp4"
    subprocess.run([sys.executable, "-m", "last.attack_video", "--video", str(SOURCE),
                    "--condition", condition, "--video-id", REPORT["video_id"],
                    "--map-seed", str(REPORT["map_seed"]), "--demo-codec-threads",
                    "--output", str(out)], check=True)
    expected = REPORT["conditions"][condition]
    assert len(load_mp4(out)) == expected["frames"]
    assert hashlib.sha256(out.read_bytes()).hexdigest() == expected["received_sha256"]


@pytest.mark.parametrize("condition", ["drop30", "drop30_crf28"])
def test_supplement_deletion_uses_published_frames_and_codec(condition, tmp_path):
    report = json.loads((ROOT / "results/public_sailboat_cpu_drop_compression.json").read_bytes())
    expected = next(row for row in report["conditions"] if row["condition"] == condition)
    output = tmp_path / condition
    subprocess.run([sys.executable, "-m", "last.stress", "--video", str(SOURCE),
                    "--video-id", report["video_id"], "--attack", condition,
                    "--seed", str(report["map_seed"]), "--demo-codec-threads",
                    "--output", str(output)], check=True)
    receipt = json.loads((output / "attack.json").read_bytes())
    assert receipt["source_sha256"] == report["source_sha256"]
    assert receipt["mapping"]["source_indices"] == report["source_indices"]
    assert receipt["frames"] == expected["frames"]
    assert hashlib.sha256((output / "received.mp4").read_bytes()).hexdigest() == expected["received_sha256"]
