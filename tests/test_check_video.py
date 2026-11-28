import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from last import check_video


@pytest.mark.parametrize("scored", [False, True])
@pytest.mark.parametrize("condition", ["drop", "duplicate30", "natural30", "drop30_crf28"])
def test_payload_only_reaches_optional_scorer(tmp_path, monkeypatch, scored, condition):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"test")
    key = tmp_path / "key"
    key.write_bytes(bytes(32))
    message = tmp_path / "message"
    output = tmp_path / "out"
    argv = ["check_video", "--video", str(video), "--video-id", "example",
            "--key", str(key), "--family", "hunyuan", "--model-dir", str(tmp_path),
            "--condition", condition, "--device", "cpu", "--output", str(output)]
    if condition == "natural30":
        argv.extend(["--donor-reference", str(tmp_path / "donor.mp4")])
    if scored:
        message.write_bytes(bytes(64))
        argv.extend(["--message", str(message)])

    calls = []
    def run(module, *args, capture=False):
        calls.append(module)
        if module == "score_message":
            assert message in args and capture
            return SimpleNamespace(stdout=json.dumps(dict(correct_bits=500, total_bits=512, bit_accuracy=500/512, exact_message=False)))
        assert message not in args
        dest = Path(args[args.index("--output") + 1])
        if module == "attack_video":
            dest.write_bytes(b"edited")
        elif module == "stress":
            assert args[args.index("--attack") + 1] == condition
            assert ("--donor-reference" in args) == (condition == "natural30")
            dest.mkdir()
            (dest / "received.mp4").write_bytes(b"edited")
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
    row = summary["results"][condition]
    assert calls == ["attack_video" if condition == "drop" else "stress", "extract"] + (["score_message"] if scored else [])
    assert row["status"] == "completed" and (output / row["prediction"]).is_file()
    assert ("correct_bits" in row) == scored
    table = (output / "summary.md").read_text(encoding="utf-8")
    assert ("500/512 | 97.66% | no" if scored else "extracted, unscored") in table


def test_failed_and_pending_conditions_have_no_scores():
    table = check_video.render_attack_table({
        "requested": ["drop", "clip"],
        "results": {"drop": {"status": "failed", "stage": "last.extract", "exit_code": 1}},
    })
    assert "| drop | failed (last.extract, exit 1) | — | — | — | — |" in table
    assert "| clip | pending | — | — | — | — |" in table


def test_interruption_and_retry_preserve_completed_predictions(tmp_path, monkeypatch):
    key = tmp_path / "key"
    video = tmp_path / "input.mp4"
    key.write_bytes(bytes(32))
    video.write_bytes(b"original")
    first = tmp_path / "first"
    second = tmp_path / "retry"
    base = ["check_video", "--key", str(key), "--video", str(video),
            "--video-id", "test", "--family", "hunyuan", "--model-dir", str(tmp_path)]
    calls = []
    interrupted = True

    def run(module, *args, capture=False):
        calls.append(module)
        dest = Path(args[args.index("--output") + 1])
        if module == "attack_video":
            assert args[args.index("--map-seed") + 1] == 2 and "--demo-codec-threads" in args
            if interrupted:
                raise KeyboardInterrupt
            dest.write_bytes(b"edited")
        else:
            dest.write_text(json.dumps({"frames": 65, "video_sha256": "digest"}))

    monkeypatch.setattr(check_video, "run_module", run)
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    monkeypatch.setattr(sys, "argv", base + ["--map-seed", "2", "--demo-codec-threads",
                                             "--output", str(first), "--condition", "clean", "--condition", "drop"])
    with pytest.raises(KeyboardInterrupt):
        check_video.main()
    original_summary = (first / "summary.json").read_bytes()
    assert json.loads(original_summary)["results"]["clean"]["status"] == "completed"

    calls.clear()
    interrupted = False
    retry = base + ["--retry-from", str(first / "summary.json"), "--output", str(second)]
    monkeypatch.setattr(sys, "argv", retry)
    check_video.main()
    assert calls == ["attack_video", "extract"]
    assert json.loads((second / "summary.json").read_bytes())["requested"] == ["drop"]
    assert (first / "summary.json").read_bytes() == original_summary
    video.write_bytes(b"different")
    monkeypatch.setattr(sys, "argv", retry[:-1] + [str(tmp_path / "wrong-source")])
    with pytest.raises(SystemExit):
        check_video.main()
    assert not (tmp_path / "wrong-source").exists()
