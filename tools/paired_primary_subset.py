"""Audit a prespecified prefix of LAST/LFG primary cases from a shared plan."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from last.report import CONDITIONS, aggregate
from last.temporal import attack_map


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(plan_path, manifest_path, root, family, mode, count, first_index=0, lfg_plan=None):
    paths = {"last": plan_path, "lfg": lfg_plan or plan_path}
    plans = {m: read(p) for m, p in paths.items()}
    manifest = read(manifest_path)
    if (any(plan["manifest_sha256"] != sha(manifest_path) for plan in plans.values())
            or first_index < 0 or count < 1 or first_index + count > len(manifest["samples"])):
        raise ValueError("Frozen manifest or requested prefix differs")
    selected = []
    hashes = {m: sha(p) for m, p in paths.items()}
    sample_ids = []
    for sample in manifest["samples"][first_index:first_index + count]:
        identity = sample["id"]
        sample_ids.append(identity)
        folders = []
        for method in ("last", "lfg"):
            relative = f"{family}/{mode}/{method}/{identity}"
            item, = [row for row in plans[method]["runs"] if row["run"] == relative]
            folder = root / relative
            campaign = read(folder / "campaign.json")
            if campaign["status"] != "completed" or campaign["plan_sha256"] != hashes[method]:
                raise ValueError(f"Missing completed job under the supplied plan: {relative}")
            case = read(folder / "case.json")
            generation = read(folder / "receipt.json")
            if (generation["status"] != "completed" or generation["case_sha256"] != sha(folder / "case.json")
                    or generation["method"] != method or case["video_id"] != identity
                    or case["seed"] != sample["seed"] or case["prompt"] != sample["prompt"]
                    or case["key_slot"] != sample["key_slot"]):
                raise ValueError(f"Generation or case differs from frozen manifest: {relative}")
            for condition in CONDITIONS:
                row = read(folder / "attacks" / (condition + ".json"))
                mapping = attack_map(identity, condition) if condition in ("drop", "insert", "clip") else None
                if row["attack_map"] != mapping or row["frames"] != (len(mapping) if mapping else 65):
                    raise ValueError(f"Unexpected attack: {relative}/{condition}")
            folders.append(folder)
            selected.append(item)
        a, b = folders
        if (read(a / "case.json") != read(b / "case.json")
                or (a / "secret.key").read_bytes() != (b / "secret.key").read_bytes()
                or not np.array_equal(np.load(a / "message.npy"), np.load(b / "message.npy"))):
            raise ValueError(f"Unpaired case, key or message for {identity}")
    scope = "Matched primary manifest slice" if first_index else "Matched primary prefix only"
    result = aggregate(dict(scope=scope, runs=selected), root, verify_artifacts=True)
    if not result["complete"]:
        raise ValueError("Requested prefix contains incomplete attacks")
    result.update(plan_sha256=hashes if lfg_plan else hashes["last"], manifest_sha256=sha(manifest_path), sample_ids=sample_ids,
                  planned_videos_per_method=len(manifest["samples"]))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "manifest", "root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--family", choices=["hunyuan", "wan22"], required=True)
    parser.add_argument("--mode", choices=["i2v", "t2v"], required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--first-index", type=int, default=0)
    parser.add_argument("--lfg-plan", type=Path, help="Separate frozen plan used by the LFG jobs")
    args = parser.parse_args()
    print(json.dumps(audit(args.plan, args.manifest, args.root, args.family, args.mode, args.count, args.first_index, args.lfg_plan),
                     indent=2, allow_nan=False))
