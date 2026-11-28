"""Evaluate primary attacks on a standalone marked MP4 without a generation run."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from .report import CONDITIONS


def run_module(module, *args, capture=False):
    return subprocess.run(
        [sys.executable, "-m", "last." + module, *map(str, args)],
        check=True, text=True, stdout=subprocess.PIPE if capture else None,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--message", type=Path, required=True, help="Original 64 bytes, used for scoring")
    parser.add_argument("--family", choices=["hunyuan", "wan22"], required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--map-seed", type=int, choices=range(5), default=0)
    parser.add_argument("--condition", choices=CONDITIONS, action="append")
    parser.add_argument("--output", type=Path, required=True, help="New private output directory")
    args = parser.parse_args()
    if args.key.stat().st_size != 32 or args.message.stat().st_size != 64:
        parser.error("Expected a 32-byte key and a 64-byte message")
    source_hash = hashlib.sha256(args.video.read_bytes()).hexdigest()
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False)
    conditions = list(dict.fromkeys(args.condition or CONDITIONS))
    summary = dict(video_id=args.video_id, family=args.family, map_seed=args.map_seed,
                   source_sha256=source_hash, requested=conditions, results={})
    for condition in conditions:
        row = summary["results"][condition] = {}
        try:
            received = args.video
            if condition != "clean":
                received = args.output / (condition + ".mp4")
                run_module("attack_video", "--video", args.video, "--video-id", args.video_id,
                           "--condition", condition, "--map-seed", args.map_seed, "--output", received)
            prediction = args.output / (condition + "-prediction.json")
            run_module("extract", "--video", received, "--key", args.key, "--family", args.family,
                       "--model-dir", args.model_dir, "--output", prediction)
            receipt = json.loads(prediction.read_bytes())
            score = run_module("score_message", "--message", args.message, "--prediction", prediction, capture=True)
            row.update(status="completed", frames=receipt["frames"], received_sha256=receipt["video_sha256"],
                       **json.loads(score.stdout))
        except subprocess.CalledProcessError as exc:
            row.update(status="failed", stage=exc.cmd[2], exit_code=exc.returncode)
        temp = args.output / "summary.tmp"
        temp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        temp.replace(args.output / "summary.json")
        print(condition, json.dumps(row), flush=True)
    if any(row["status"] == "failed" for row in summary["results"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
