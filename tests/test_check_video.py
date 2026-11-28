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
        (tmp_path / "donor.mp4").write_bytes(b"original donor")
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


def test_table15_runs_all_edits_at_one_seed(tmp_path, monkeypatch):
    video, key, donor, output = [tmp_path / n for n in ("source", "key", "donor", "out")]
    video.write_bytes(b"original")
    key.write_bytes(bytes(32))
    donor.write_bytes(b"donor")
    edits = []

    def run(module, *args):
        dest = Path(args[args.index("--output") + 1])
        if module == "stress":
            condition = args[args.index("--attack") + 1]
            assert args[args.index("--seed") + 1] == 3
            assert (donor in args) == (condition == "natural30")
            edits.append(condition)
            dest.mkdir()
            (dest / "received.mp4").write_bytes(b"edited")
        else:
            assert module == "extract"
            assert Path(args[args.index("--video") + 1]) == output / edits[-1] / "received.mp4"
            dest.write_text(json.dumps({"frames": 35, "video_sha256": "digest"}))

    monkeypatch.setattr(check_video, "run_module", run)
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    monkeypatch.setattr(sys, "argv", ["check_video", "--video", str(video), "--key", str(key),
                        "--video-id", "demo", "--family", "hunyuan", "--model-dir", str(tmp_path),
                        "--table15", "--map-seed", "3", "--donor-reference", str(donor), "--output", str(output)])
    check_video.main()
    summary = json.loads((output / "summary.json").read_bytes())
    assert edits == summary["requested"] == list(check_video.STRESS_CONDITIONS)
    assert all(row["status"] == "completed" for row in summary["results"].values())


def test_failed_and_pending_conditions_have_no_scores():
    table = check_video.render_attack_table({
        "requested": ["drop", "clip"],
        "results": {"drop": {"status": "failed", "stage": "last.extract", "exit_code": 1}},
    })
    assert "| drop | failed (last.extract, exit 1) | — | — | — | — |" in table
    assert "| clip | pending | — | — | — | — |" in table


@pytest.mark.parametrize("completed", ["clean", "natural30"])
def test_interruption_and_retry_preserve_completed_predictions(tmp_path, monkeypatch, completed):
    key = tmp_path / "key"
    video = tmp_path / "input.mp4"
    key.write_bytes(bytes(32))
    video.write_bytes(b"original")
    first = tmp_path / "first"
    second = tmp_path / "retry"
    base = ["check_video", "--key", str(key), "--video", str(video),
            "--video-id", "test", "--family", "hunyuan", "--model-dir", str(tmp_path)]
    if completed == "natural30":
        donor = tmp_path / "donor.mp4"
        donor.write_bytes(b"original donor")
        base += ["--donor-reference", str(donor)]
    calls = []
    interrupted = True

    def run(module, *args, capture=False):
        calls.append(module)
        dest = Path(args[args.index("--output") + 1])
        if module == "stress":
            dest.mkdir()
            (dest / "received.mp4").write_bytes(b"edited")
        elif module == "attack_video":
            assert args[args.index("--map-seed") + 1] == 2 and "--demo-codec-threads" in args
            if interrupted:
                raise KeyboardInterrupt
            dest.write_bytes(b"edited")
        else:
            dest.write_text(json.dumps({"frames": 65, "video_sha256": "digest"}))

    monkeypatch.setattr(check_video, "run_module", run)
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    monkeypatch.setattr(sys, "argv", base + ["--map-seed", "2", "--demo-codec-threads",
                                             "--output", str(first), "--condition", completed, "--condition", "drop"])
    with pytest.raises(KeyboardInterrupt):
        check_video.main()
    original_summary = (first / "summary.json").read_bytes()
    assert json.loads(original_summary)["results"][completed]["status"] == "completed"

    calls.clear()
    interrupted = False
    retry = base + ["--retry-from", str(first / "summary.json"), "--output", str(second)]
    monkeypatch.setattr(sys, "argv", retry)
    check_video.main()
    assert calls == ["attack_video", "extract"]
    assert json.loads((second / "summary.json").read_bytes())["requested"] == ["drop"]
    assert (first / "summary.json").read_bytes() == original_summary
    key.write_bytes(b"x" * 32)
    monkeypatch.setattr(sys, "argv", retry[:-1] + [str(tmp_path / "wrong-key")])
    with pytest.raises(SystemExit):
        check_video.main()
    assert not (tmp_path / "wrong-key").exists()
    key.write_bytes(bytes(32))
    video.write_bytes(b"different")
    monkeypatch.setattr(sys, "argv", retry[:-1] + [str(tmp_path / "wrong-source")])
    with pytest.raises(SystemExit):
        check_video.main()
    assert not (tmp_path / "wrong-source").exists()

@pytest.mark.parametrize("replacement", [None, b"B" * 64])
def test_retry_rejects_missing_or_changed_scoring_message(tmp_path, monkeypatch, replacement):
    video, key, message = (tmp_path / n for n in ("video", "key", "message"))
    video.write_bytes(b"source")
    key.write_bytes(bytes(32))
    message.write_bytes(b"A" * 64)
    base = ["check_video", "--video", str(video), "--video-id", "case", "--key", str(key),
            "--family", "hunyuan", "--model-dir", str(tmp_path)]
    first, retry = tmp_path / "first", tmp_path / "retry"
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(check_video, "run_module", interrupt)
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    monkeypatch.setattr(sys, "argv", base + ["--message", str(message), "--condition", "clean", "--output", str(first)])
    with pytest.raises(KeyboardInterrupt):
        check_video.main()
    if replacement is not None:
        message.write_bytes(replacement)
        base += ["--message", str(message)]
    monkeypatch.setattr(sys, "argv", base + ["--retry-from", str(first / "summary.json"), "--output", str(retry)])
    with pytest.raises(SystemExit):
        check_video.main()
    assert not retry.exists()


def test_reject_changed_donor_before_retry(tmp_path, monkeypatch):
    video, donor, key = (tmp_path / n for n in ("source", "donor", "key"))
    video.write_bytes(b"source")
    donor.write_bytes(b"first donor")
    key.write_bytes(bytes(32))
    base = ["check_video", "--video", str(video), "--video-id", "case", "--key", str(key),
            "--family", "hunyuan", "--model-dir", str(tmp_path), "--donor-reference", str(donor)]
    output = tmp_path / "first"
    monkeypatch.setattr(sys, "argv", base + ["--condition", "natural30", "--output", str(output)])
    monkeypatch.setattr(check_video.os, "umask", lambda mode: None)
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(check_video, "run_module", interrupt)
    with pytest.raises(KeyboardInterrupt):
        check_video.main()
    donor.write_bytes(b"second donor")
    retry = tmp_path / "retry"
    monkeypatch.setattr(sys, "argv", base + ["--retry-from", str(output / "summary.json"), "--output", str(retry)])
    with pytest.raises(SystemExit):
        check_video.main()
    assert not retry.exists()
