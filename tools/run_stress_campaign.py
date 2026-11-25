"""Run supplementary Table 15 for one primary pipeline, optionally by shard (Linux)."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from last.campaign import digest, source_digest
from last.data import validate
from last.stress_donors import resolve
from export_stress_counts import export, reader_identity
from stress_recovery_table import ATTACKS


def evaluate_case(args, sample, directory):
    video = sample["id"]
    run = args.runs / video
    generation = json.loads((run / "receipt.json").read_bytes())
    case_bytes = (run / "case.json").read_bytes()
    case = json.loads(case_bytes)
    if (generation["status"] != "completed" or generation["method"] != "last"
            or generation["family"] != args.family or generation["mode"] != args.mode
            or generation["case_sha256"] != hashlib.sha256(case_bytes).hexdigest()
            or case["video_id"] != video or case["prompt"] != sample["prompt"]
            or case["seed"] != sample["seed"] or generation["marked_sha256"] != digest(run / "marked.mp4")):
        raise ValueError(f"Generation differs from manifest for {video}")
    edits = directory / "edits"
    scores = directory / "scores"
    edits.mkdir(exist_ok=True)
    for attack in ATTACKS:
        target = edits / attack
        donor_args = []
        if attack == "natural30":
            donor, donor_id = resolve(args.donor_plan, args.manifest, args.runs, video)
            donor_sha = digest(donor)
            plan_sha = digest(args.donor_plan)
            donor_args = ["--donor-plan", args.donor_plan, "--manifest", args.manifest,
                          "--reference-root", args.runs]
        if not target.exists():
            # Only expose the five-map directory once the exporter finishes successfully.
            with tempfile.TemporaryDirectory(dir=directory) as temp:
                pending = Path(temp) / attack
                subprocess.run([sys.executable, "-m", "last.stress", "--video", run / "marked.mp4",
                                "--video-id", video, "--attack", attack, "--all-seeds",
                                "--output", pending, *donor_args], check=True)
                pending.rename(target)
        if {p.name for p in target.iterdir()} != {f"map{i}" for i in range(5)}:
            raise ValueError(f"Incomplete map set in {target}")
        for seed in range(5):
            record = json.loads((target / f"map{seed}" / "attack.json").read_bytes())
            if (record["attack"], record["video_id"], record["seed"]) != (attack, video, seed):
                raise ValueError(f"Wrong map identity in {target}")
            if attack == "natural30" and (record.get("donor_sha256") != donor_sha
                    or record.get("donor_video_id") != donor_id
                    or record.get("donor_plan_sha256") != plan_sha):
                raise ValueError("Cached insertion differs from the assigned donor")
    subprocess.run([sys.executable, "-m", "last.stress_evaluate", "--run", run,
                    "--attacks", edits, "--output", scores, "--family", args.family,
                    "--model-dir", args.model_dir], check=True)
    report = export(run, edits, scores, args.reader_repo, alignment=True)
    pending = directory / "counts.tmp"
    pending.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    pending.replace(directory / "counts.json")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("runs", "model-dir", "output", "reader-repo"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    p.add_argument("--donor-plan", type=Path, default=Path("configs/stress_donors.json"))
    p.add_argument("--family", choices=["hunyuan", "wan22"], required=True)
    p.add_argument("--mode", choices=["i2v", "t2v"], required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    args = p.parse_args()
    if not 0 <= args.shard < args.shards:
        p.error("Expected 0 <= shard < shards")
    manifest = json.loads(args.manifest.read_bytes())
    validate(manifest)
    if reader_identity(args.reader_repo)[1] != source_digest():
        p.error("Installed LAST source differs from the selected reader revision")
    os.umask(0o077)
    for i, sample in enumerate(manifest["samples"]):
        if i % args.shards != args.shard:
            continue
        directory = args.output / sample["id"]
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "worker.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            evaluate_case(args, sample, directory)


if __name__ == "__main__":
    main()
