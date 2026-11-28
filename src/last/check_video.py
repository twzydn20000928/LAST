"""Evaluate primary and supplementary attacks on a standalone marked MP4 without a generation run."""
import argparse
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

from .models import file_hash
from .report import CONDITIONS
from .stress_conditions import STRESS_CONDITIONS


def run_module(module, *args, capture=False):
    return subprocess.run(
        [sys.executable, "-m", "last." + module, *map(str, args)],
        check=True, text=True, stdout=subprocess.PIPE if capture else None,
    )


def render_attack_table(summary):
    lines = [
        "| Condition | Status | Received frames | Correct bits | Bit accuracy | Exact message |",
        "|---|---|---:|---:|---:|---|",
    ]
    for condition in summary["requested"]:
        row = summary["results"].get(condition, {})
        status = row.get("status", "pending")
        bits = accuracy = exact = "—"
        if status == "failed":
            status = f"failed ({row['stage']}, exit {row['exit_code']})"
        elif status == "completed" and "correct_bits" in row:
            bits = f"{row['correct_bits']}/{row['total_bits']}"
            accuracy = f"{row['bit_accuracy']:.2%}"
            exact = "yes" if row["exact_message"] else "no"
        elif status == "completed":
            status = "extracted, unscored"
        lines.append(f"| {condition} | {status} | {row.get('frames', '—')} | {bits} | {accuracy} | {exact} |")
    return "\n".join(lines) + "\n"


def save_progress(output, summary):
    for name, content in (("summary.json", json.dumps(summary, indent=2) + "\n"),
                          ("summary.md", render_attack_table(summary))):
        target = output / name
        temporary = target.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--message", type=Path, help="Optional original 64 bytes for scoring after blind extraction")
    parser.add_argument("--family", choices=["hunyuan", "wan22"], required=True)
    parser.add_argument("--progress", action="store_true", help="Report candidate windows on stderr")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda", help="Device for blind extraction")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--map-seed", type=int, choices=range(5))
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--retry-from", type=Path, help="Run unfinished conditions from a previous summary in a new directory")
    selection.add_argument("--condition", choices=[*CONDITIONS, *STRESS_CONDITIONS], action="append",
                        help="Repeat to select edits; defaults to the seven primary conditions")
    parser.add_argument("--output", type=Path, required=True, help="New private output directory")
    parser.add_argument("--demo-codec-threads", action="store_true",
                        help="Use the public demo encoder settings (16 x264 threads, 2 lookahead threads)")
    parser.add_argument("--donor-reference", type=Path, help="Unmarked same-resolution video for natural30")
    args = parser.parse_args()
    key = args.key.read_bytes()
    if len(key) != 32:
        parser.error("Expected a 32-byte key")
    if args.message is not None and args.message.stat().st_size != 64:
        parser.error("Expected a 64-byte message for scoring")
    source_hash = file_hash(args.video)
    retry_tag = hmac.digest(key, b"LAST single-video retry v1" + bytes.fromhex(source_hash), "sha256").hex()
    scoring_tag = None
    if args.message is not None:
        scoring_tag = hmac.digest(key, b"LAST scoring payload v1" + bytes.fromhex(source_hash)
                                  + args.message.read_bytes(), "sha256").hex()
    conditions = list(dict.fromkeys(args.condition or CONDITIONS))
    if args.retry_from:
        previous = json.loads(args.retry_from.read_bytes())
        if (previous["source_sha256"], previous["video_id"], previous["family"]) != (
                source_hash, args.video_id, args.family):
            parser.error("Retry requires the same source MP4, video ID and model family")
        if "retry_key_tag" in previous and not hmac.compare_digest(previous["retry_key_tag"], retry_tag):
            parser.error("Retry key differs from the original extraction key")
        if "scoring_payload_tag" in previous and previous["scoring_payload_tag"] != scoring_tag:
            parser.error("Retry requires the same scoring message or the same unscored mode")
        if args.map_seed is not None and args.map_seed != previous["map_seed"]:
            parser.error("Retry must use the previous map seed")
        args.map_seed = previous["map_seed"]
        prior_threads = previous.get("demo_codec_threads")
        if prior_threads is False and args.demo_codec_threads:
            parser.error("Retry must use the previous codec settings")
        if prior_threads is not None:
            args.demo_codec_threads = prior_threads
        conditions = [c for c in previous["requested"]
                      if previous["results"].get(c, {}).get("status") != "completed"]
        if not conditions:
            parser.error("All requested conditions already completed")
        if any(c not in (*CONDITIONS, *STRESS_CONDITIONS) for c in conditions):
            parser.error("Unknown condition in retry summary")
        if "natural30" in previous["requested"] and "natural30" not in conditions:
            # The completed insertion stays in the original directory.
            args.donor_reference = None
    if args.map_seed is None:
        args.map_seed = 0
    if ("natural30" in conditions) != (args.donor_reference is not None):
        parser.error("Select natural30 together with --donor-reference")
    donor_hash = file_hash(args.donor_reference) if args.donor_reference else None
    if donor_hash and args.retry_from and previous.get("donor_sha256", donor_hash) != donor_hash:
        parser.error("Retry donor differs from the original natural30 donor")
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False)
    summary = dict(video_id=args.video_id, family=args.family, device=args.device,
                   demo_codec_threads=args.demo_codec_threads, map_seed=args.map_seed,
                   source_sha256=source_hash, retry_key_tag=retry_tag, scoring_payload_tag=scoring_tag,
                   requested=conditions, results={})
    if donor_hash:
        summary["donor_sha256"] = donor_hash
    save_progress(args.output, summary)
    for condition in conditions:
        row = summary["results"][condition] = {}
        try:
            received = args.video
            if condition in STRESS_CONDITIONS:
                directory = args.output / condition
                run_module("stress", "--video", args.video, "--video-id", args.video_id,
                           "--attack", condition, "--seed", args.map_seed, "--output", directory,
                           *(["--donor-reference", args.donor_reference] if condition == "natural30" else []),
                           *(["--demo-codec-threads"] if args.demo_codec_threads else []))
                received = directory / "received.mp4"
            elif condition != "clean":
                received = args.output / (condition + ".mp4")
                run_module("attack_video", "--video", args.video, "--video-id", args.video_id,
                           "--condition", condition, "--map-seed", args.map_seed, "--output", received,
                           *(["--demo-codec-threads"] if args.demo_codec_threads else []))
            prediction = args.output / (condition + "-prediction.json")
            run_module("extract", "--video", received, "--key", args.key, "--family", args.family,
                       "--model-dir", args.model_dir, "--device", args.device, "--output", prediction,
                       *(["--progress"] if args.progress else []))
            receipt = json.loads(prediction.read_bytes())
            row.update(frames=receipt["frames"], received_sha256=receipt["video_sha256"],
                       prediction=prediction.name)
            if args.message is not None:
                score = run_module("score_message", "--message", args.message,
                                   "--prediction", prediction, capture=True)
                row.update(json.loads(score.stdout))
            row["status"] = "completed"
        except subprocess.CalledProcessError as exc:
            row.update(status="failed", stage=exc.cmd[2], exit_code=exc.returncode)
        save_progress(args.output, summary)
        print(condition, json.dumps(row), flush=True)
    if any(row["status"] == "failed" for row in summary["results"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
