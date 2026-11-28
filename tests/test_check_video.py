import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from last import check_video


@pytest.mark.parametrize("scored", [False, True])
def test_payload_only_reaches_optional_scorer(tmp_path, monkeypatch, scored):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"test")
    key = tmp_path / "key"
    key.write_bytes(bytes(32))
    message = tmp_path / "message"
    output = tmp_path / "out"
    argv = ["check_video", "--video", str(video), "--video-id", "example",
            "--key", str(key), "--family", "hunyuan", "--model-dir", str(tmp_path),
            "--condition", "drop", "--device", "cpu", "--output", str(output)]
    if scored:
        message.write_bytes(bytes(64))
        argv.extend(["--message", str(message)])

    calls = []
    def run(module, *args, capture=False):
        calls.append(module)
        if module == "score_message":
            assert message in args and capture
            return SimpleNamespace(stdout='{"correct_bits": 500}')
        assert message not in args
        dest = Path(args[args.index("--output") + 1])
        if module == "attack_video":
            dest.write_bytes(b"edited")
        else:
            assert args[args.index("--device") + 1] == "cpu"
            assert Path(args[args.index("--video") + 1]).read_bytes() == b"edited"
            dest.write_text(json.dumps(dict(frames=35, video_sha256="digest")))

    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(check_video, "run_module", run)
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    check_video.main()
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["device"] == "cpu" and summary["demo_codec_threads"] is False
    row = summary["results"]["drop"]
    assert calls == ["attack_video", "extract"] + (["score_message"] if scored else [])
    assert row["status"] == "completed" and (output / row["prediction"]).is_file()
    assert ("correct_bits" in row) == scored
