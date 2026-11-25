"""Audit one primary pipeline from a multi-pipeline generation plan."""
import argparse
import hashlib
import json
from pathlib import Path

from last.data import validate
from last.report import aggregate


def audit(plan_path, manifest_path, root, family, mode, method):
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    validate(manifest)
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_digest != plan["manifest_sha256"]:
        raise ValueError("Primary manifest differs from the generation plan")
    runs = [r for r in plan["runs"] if (r["family"], r["mode"], r["method"]) == (family, mode, method)]
    if sorted(r["video_id"] for r in runs) != sorted(s["id"] for s in manifest["samples"]):
        raise ValueError("Plan must cover every primary video exactly once for this pipeline")
    samples = {s["id"]: s for s in manifest["samples"]}
    for item in runs:
        video = item["video_id"]
        sample = samples[video]
        if (item["index"], item["key_slot"], item["run"]) != (
                sample["index"], sample["key_slot"], f"{family}/{mode}/{method}/{video}"):
            raise ValueError(f"Planned sample assignment differs from manifest: {video}")
    scope = f"{family} {mode} {method}: measured primary attacks with archived MP4 verification"
    result = aggregate(dict(plan, runs=runs, scope=scope), root, verify_artifacts=True)
    measured_ids = {row["video_id"] for row in result["audited_observations"]}
    for video in sorted(measured_ids):
        folder = root / family / mode / method / video
        case_bytes = (folder / "case.json").read_bytes()
        case = json.loads(case_bytes)
        receipt = json.loads((folder / "receipt.json").read_bytes())
        sample = samples[video]
        expected = (video, sample["prompt"], sample["seed"], sample["key_slot"])
        if (case["video_id"], case["prompt"], case["seed"], case["key_slot"]) != expected:
            raise ValueError(f"Generation inputs differ from manifest: {video}")
        if hashlib.sha256(case_bytes).hexdigest() != receipt["case_sha256"]:
            raise ValueError(f"Generation receipt refers to a different case: {video}")
    result.update(plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
                  manifest_sha256=manifest_digest,
                  planned_videos_per_method=len(runs))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--family", choices=("hunyuan", "wan22"), required=True)
    parser.add_argument("--mode", choices=("t2v", "i2v"), required=True)
    parser.add_argument("--method", choices=("last", "lfg"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.plan, args.manifest, args.root, args.family, args.mode, args.method)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
