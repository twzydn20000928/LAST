"""Recount the original Hunyuan LAST deletion receipts and verify both MP4 files."""
import argparse
import hashlib
import json
from pathlib import Path

from last.data import validate
from last.message_outcomes import summarize
from last.temporal import attack_map


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root, manifest, condition="drop", selected=None):
    validate(manifest)
    rows, observations, legacy = [], [], []
    for sample in manifest["samples"]:
        video_id = sample["id"]
        if selected is not None and video_id not in selected:
            continue
        folder = root / "hunyuan" / "i2v" / "last" / video_id
        receipt = folder / "attacks" / (condition + ".json")
        if not receipt.exists():
            continue
        row = json.loads(receipt.read_bytes())
        if row["status"] != "completed":
            continue
        if "received_sha256" not in row:
            legacy.append(video_id)
            continue
        case = json.loads((folder/"case.json").read_bytes())
        mapping = attack_map(video_id, condition) if condition in ("drop", "insert", "clip") else None
        received = folder/"marked.mp4" if condition == "clean" else folder/"attacks"/(condition + ".mp4")
        if (row["video_id"] != video_id or case["video_id"] != video_id
                or (case["seed"], case["prompt"], case["key_slot"]) != (sample["seed"], sample["prompt"], sample["key_slot"])
                or row["method"] != "last" or row["condition"] != condition or row.get("map_seed", 0) != 0
                or row["attack_map"] != mapping or row["frames"] != (len(mapping) if mapping is not None else 65)
                or row["source_sha256"] != digest(folder/"marked.mp4")
                or row["received_sha256"] != digest(received)):
            raise ValueError(f"Primary case, map or MP4 mismatch: {video_id}")
        rows.append(row)
        observations.append(dict(video_id=video_id, receipt_sha256=digest(receipt), **{
            k:row.get(k) for k in ("received_sha256", "correct_bits", "raw_information_correct", "bch_success")}))
    return dict(scope="Original attack receipts with MP4 and primary-map checks", observations=observations,
                excluded_missing_received_hash=legacy,
                summary=summarize(rows, [s["id"] for s in manifest["samples"]]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path, help="Private directory containing generated MP4s and original attack receipts")
    source.add_argument("--report", type=Path, help="Public per-video counts exported with --root")
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    if args.report:
        validate(manifest)
        public = json.loads(args.report.read_bytes())
        if public["manifest_sha256"] != digest(args.manifest):
            raise ValueError("Manifest differs from the acquisition manifest")
        rows = [dict(row, status="completed", total_bits=512, exact_message=row["correct_bits"] == 512)
                for row in public["observations"]]
        result = summarize(rows, [s["id"] for s in manifest["samples"]])
        if result != public["summary"]:
            raise ValueError("Released summary differs from per-video counts")
        result.pop("incomplete_ids")
        result.pop("error_histogram")
    else:
        result = collect(args.root, manifest)
        result["manifest_sha256"] = digest(args.manifest)
    print(json.dumps(result, indent=2, allow_nan=False))
