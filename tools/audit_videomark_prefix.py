"""Recount native baseline readouts and verify pairing with primary LAST cases."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from last.baseline_evaluate import check_extraction
from last.data import validate
from last.report import CONDITIONS, aggregate
from last.temporal import attack_map


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit(root, manifest_path, plan_path, count, method="videomark", mode="t2v", family="hunyuan",
          allow_incomplete=False, retry_dirs=None):
    manifest, plan = read(manifest_path), read(plan_path)
    validate(manifest)
    if plan["manifest_sha256"] != sha(manifest_path) or not 1 <= count <= len(manifest["samples"]):
        raise ValueError("Unexpected primary manifest or prefix")
    items = []
    retry_dirs = retry_dirs or {}
    legacy = 0
    recounted = {}
    for sample in manifest["samples"][:count]:
        video = sample["id"]
        relative = f"{family}/{mode}/{method}/{video}"
        item, = [i for i in plan["runs"] if i["run"] == relative]
        if (item["family"], item["mode"], item["method"], item["video_id"], item["index"], item["key_slot"]) != (
                family, mode, method, video, sample["index"], sample["key_slot"]):
            raise ValueError(f"Native plan differs from frozen sample: {video}")
        folder = root / relative
        last = root / family / mode / "last" / video
        case_path = root / ".native-jobs" / (relative.replace("/", "__") + ".case.json")
        generation = read(folder / "receipt.json")
        if generation["case_sha256"] != sha(case_path) or generation["seed"] != sample["seed"]:
            raise ValueError(f"Native generation input mismatch: {video}")
        for case in (read(case_path), read(last / "case.json")):
            if (case["prompt"], case["seed"], case["video_id"]) != (sample["prompt"], sample["seed"], video):
                raise ValueError(f"Unmatched primary sample: {video}")
            if mode == "i2v" and sha(Path(case["image"])) != sample["image_sha256"]:
                raise ValueError(f"Conditioning image differs from frozen manifest: {video}")
        truth = (folder / "message.bin").read_bytes()
        bits = np.unpackbits(np.frombuffer(truth, dtype=np.uint8))
        if len(truth) != 64 or not np.array_equal(bits, np.load(last / "message.npy", allow_pickle=False)):
            raise ValueError(f"Unmatched message: {video}")
        state = sha(folder / "maintained_private.pkl")
        for condition in CONDITIONS:
            temporal = condition in ("drop", "insert", "clip")
            path = folder / "attacks"
            retry = retry_dirs.get((relative, condition))
            if retry is not None:
                from recount_native_attack import recount
                recount(folder, condition, video, legacy=True, retry_directory=retry)
                path = retry
            score = path / (condition + ".json")
            if allow_incomplete and not score.exists():
                continue
            score_bytes = score.read_bytes()
            row = json.loads(score_bytes)
            if row["status"] != "completed":
                if allow_incomplete:
                    continue
                raise ValueError(f"Native observation {video}/{condition} has status {row['status']}")
            reader = path / (condition + "-extract")
            receipt = read(reader / "receipt.json")
            mapping = attack_map(video, condition) if temporal else None
            if (row["attack_map"] != mapping or read(last / "attacks" / (condition + ".json"))["attack_map"] != mapping
                    or row["frames"] != (len(mapping) if temporal else 65)):
                raise ValueError(f"Unmatched edit: {video}/{condition}")
            check_extraction(receipt, method, mode, row["received_sha256"], state, temporal, family)
            if row["extraction_receipt_sha256"] != sha(reader / "receipt.json") or row["state_sha256"] != state:
                raise ValueError(f"Changed extraction evidence: {video}/{condition}")
            prediction = (reader / "decoded.bin").read_bytes()
            decoded_sha = hashlib.sha256(prediction).hexdigest()
            for record in (row, receipt):
                if "decoded_sha256" in record and record["decoded_sha256"] != decoded_sha:
                    raise ValueError("Changed prediction")
            # A later recount can hash a reused prediction but cannot establish its earlier history.
            legacy += "decoded_sha256" not in receipt and ("decoded_sha256" not in row or row.get("reused_extraction", False))
            if len(prediction) != 64 or sum((a ^ b).bit_count() for a, b in zip(truth, prediction)) != 512 - row["correct_bits"]:
                raise ValueError(f"Native prediction recount mismatch: {video}/{condition}")
            recounted[video, condition] = hashlib.sha256(score_bytes).hexdigest()
        items.append(item)
    family_label = {"hunyuan": "Hunyuan", "wan22": "Wan-2.2"}[family]
    report = aggregate(dict(scope=f"Matched {family_label} {mode} {method} primary prefix", runs=items), root,
                       verify_artifacts=True, native_retry_dirs=retry_dirs)
    if not allow_incomplete and not report["complete"]:
        raise ValueError("Missing native measurements")
    aggregated = {(r["video_id"], r["condition"]): r["receipt_sha256"] for r in report["audited_observations"]}
    if not recounted or recounted != aggregated:
        raise ValueError("No verified measurements or receipts changed during the recount")
    return dict(report, sample_ids=[i["video_id"] for i in items], planned_videos_per_method=len(manifest["samples"]),
                manifest_sha256=sha(manifest_path), plan_sha256=sha(plan_path),
                recounted_predictions=len(recounted), predictions_without_historical_digest=legacy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("root", "manifest", "plan", "output"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--method", choices=("videomark", "videoshield", "sigmark"), default="videomark")
    parser.add_argument("--mode", choices=("t2v", "i2v"), default="t2v")
    parser.add_argument("--family", choices=("hunyuan", "wan22"), default="hunyuan")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Retain missing and failed conditions while verifying each completed prediction")
    parser.add_argument("--retry", nargs=3, action="append", default=[], metavar=("VIDEO_ID", "CONDITION", "DIRECTORY"),
                        help="Recount a completed retry of the original failed attack")
    args = parser.parse_args()
    retry_dirs = {}
    for video, condition, directory in args.retry:
        key = (f"{args.family}/{args.mode}/{args.method}/{video}", condition)
        if key in retry_dirs:
            parser.error("Duplicate retry for one video and condition")
        retry_dirs[key] = Path(directory)
    result = audit(args.root, args.manifest, args.plan, args.count, args.method, args.mode, args.family,
                   args.allow_incomplete, retry_dirs)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
