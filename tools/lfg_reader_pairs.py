"""Recount paired LFG original/CCTA predictions on the unchanged primary MP4s."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from last.report import CONDITIONS
from last.data import validate
from last.temporal import attack_map


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(report, root, outputs, samples):
    rows = []
    for sample in samples:
        video = sample["id"]
        folder = root/"hunyuan"/"i2v"/"lfg"/video
        case = json.loads((folder/"case.json").read_bytes())
        if case["video_id"] != video or any(case[k] != sample[k] for k in ("prompt", "seed", "key_slot")):
            raise ValueError(f"Primary case mismatch: {video}")
        source_hash = digest(folder/"marked.mp4")
        truth = np.load(folder/"message.npy", allow_pickle=False)
        if truth.shape != (512,) or not np.isin(truth, [0, 1]).all():
            raise ValueError("Invalid private primary message")
        prior = [r for r in report["audited_observations"] if
                 (r["family"], r["mode"], r["method"], r["video_id"]) == ("hunyuan", "i2v", "lfg", video)] if report else []
        receipt = outputs/video/"receipt.json"
        receipt_bytes = receipt.read_bytes()
        new = json.loads(receipt_bytes)
        receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
        for group in ([prior, new["rows"]] if report else [new["rows"]]):
            if sorted(r["condition"] for r in group) != sorted(CONDITIONS):
                raise ValueError(f"Incomplete conditions: {video}")
        if new["status"] != "completed":
            raise ValueError(f"Incomplete extraction: {video}")
        original = {r["condition"]: r for r in prior}
        for r in new["rows"]:
            c = r["condition"]
            attack = folder/"attacks"/(c+".json")
            mp4 = folder/"marked.mp4" if c == "clean" else folder/"attacks"/(c+".mp4")
            base = json.loads(attack.read_bytes())
            mapping = attack_map(video, c) if c in ("drop", "insert", "clip") else None
            attack_hash = digest(attack)
            if (base["status"] != "completed" or base.get("map_seed", 0) != 0
                    or (base["method"], base["video_id"], base["condition"]) != ("lfg", video, c)
                    or base["attack_map"] != mapping or base["source_sha256"] != source_hash
                    or base["total_bits"] != 512 or not 0 <= base["correct_bits"] <= 512
                    or digest(mp4) != r["received_sha256"] or r["received_sha256"] != base["received_sha256"]):
                raise ValueError(f"Unmatched attack: {video}/{c}")
            if report and (original[c]["receipt_sha256"] != attack_hash or
                           original[c]["correct_bits"] != base["correct_bits"] or
                           original[c]["video_sha256"] != r["received_sha256"]):
                raise ValueError(f"Released baseline differs: {video}/{c}")
            prediction = np.load(outputs/video/(c+"_prediction_private.npy"), allow_pickle=False)
            if prediction.shape != truth.shape or not np.isin(prediction, [0, 1]).all():
                raise ValueError("Invalid private prediction")
            correct = int(np.count_nonzero(prediction == truth))
            if r["correct_bits"] != correct or r["total_bits"] != 512 or r["exact_message"] is not (correct == 512):
                raise ValueError(f"Recount differs: {video}/{c}")
            rows.append(dict(video_id=video, condition=c, original_bits=base["correct_bits"],
                             ccta_bits=correct, total_bits=512, received_sha256=r["received_sha256"],
                             original_bch_success=base["bch_success"], ccta_bch_success=r["bch_success"],
                             ccta_route=r["route"], ccta_groups=r["groups"], reader_source_sha256=new["source_sha256"],
                             original_receipt_sha256=attack_hash, ccta_receipt_sha256=receipt_hash))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "outputs"):
        parser.add_argument("--"+name, required=True, type=Path)
    parser.add_argument("--report", type=Path, help="Also compare an earlier baseline from these exact videos")
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    validate(manifest)
    samples = manifest["samples"][:args.count]
    if not 1 <= args.count <= len(manifest["samples"]):
        parser.error("Count exceeds the primary sample list")
    ids = [s["id"] for s in samples]
    report = json.loads(args.report.read_bytes()) if args.report else None
    if report and ids != report["sample_ids"][:args.count]:
        raise ValueError("Earlier baseline has a different primary prefix")
    print(json.dumps(dict(sample_ids=ids, manifest_sha256=digest(args.manifest),
                          primary_report_sha256=digest(args.report) if report else None,
                          observations=audit(report,args.root,args.outputs,samples)), indent=2))
