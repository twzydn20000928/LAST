"""Join original paired-reference fidelity to the exact Tables 10–11 cohort."""
import argparse
import json
from pathlib import Path
from paired_oracle_table import load_blind_report

from last.data import validate
from last.report import CONDITIONS
from last.fidelity_summary import summarize
from paired_prefix_fidelity import digest, measurement
from primary_message_tables import summaries


def audit(root, manifest, report, frozen_first100=None):
    validate(manifest)
    if frozen_first100 is not None or "audited_observations" in report:
        if frozen_first100 is None and not report["artifact_verification"]:
            raise ValueError("Require an artifact-verified attack report")
        checked = (frozen_first100 or report)["audited_observations"]
        targets = {(r["family"], r["mode"], r["method"]) for r in checked}
        if len(targets) != 1:
            raise ValueError("Expected a single method and generation pipeline")
        family, mode, method = targets.pop()
        ids = sorted({r["video_id"] for r in checked})
        pairs = {(r["video_id"], r["condition"]) for r in checked}
        if len(pairs) != len(checked) or pairs != {(i, c) for i in ids for c in CONDITIONS}:
            raise ValueError("Expected each video to have all seven completed conditions")
        clean_rows = [dict(r, received_sha256=r["video_sha256"]) for r in checked if r["condition"] == "clean"]
    else:
        summaries(report, manifest)
        family, mode, method = "hunyuan", "i2v", "last"
        clean_rows = report["observations"]["clean"]
        ids = report["sample_ids"]
    samples = {s["id"]: s for s in manifest["samples"]}
    rows = []
    for clean in clean_rows:
        video = clean["video_id"]
        folder = root / family / mode / method / video
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unexpected run path")
        case = json.loads((folder/"case.json").read_bytes())
        g = json.loads((folder/"receipt.json").read_bytes())
        sample = samples[video]
        if (digest(folder/"attacks"/"clean.json") != clean["receipt_sha256"]
                or g["case_sha256"] != digest(folder/"case.json")
                or (g["family"], g["mode"], g["method"], g["status"]) != (family, mode, method, "completed")
                or (case["video_id"], case["seed"], case["prompt"], case["key_slot"])
                != (video, sample["seed"], sample["prompt"], sample["key_slot"])):
            raise ValueError(f"Generation differs from primary clean sample: {video}")
        rows.append(measurement(folder, g, video, clean["received_sha256"]))
    return dict(family=family, mode=mode, method=method, sample_ids=ids,
                observations={method: rows}, cells={method: summarize(rows, list(samples))})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--additional-report", type=Path, action="append", default=[],
                        help="Include a disjoint set of videos from the same pipeline")
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    fingerprint = digest(args.manifest)
    parts = []
    reports = [args.report, *args.additional_report]
    for path in reports:
        original = json.loads(path.read_bytes())
        if original.get("manifest_sha256", fingerprint) != fingerprint:
            raise ValueError("Primary manifest mismatch")
        first100 = (load_blind_report(path, args.manifest)
                    if original.get("scope") == "First 100 frozen Hunyuan I2V LAST samples" else None)
        parts.append(audit(args.root, manifest, original, first100))
    result = parts[0]
    if len(parts) > 1:
        method = result["method"]
        if any(any(p[k] != result[k] for k in ("family", "mode", "method")) for p in parts):
            raise ValueError("Fidelity reports use different pipelines")
        rows = [r for part in parts for r in part["observations"][method]]
        ids = [row["video_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("Fidelity cohorts overlap")
        result.update(sample_ids=ids, observations={method: rows},
                      cells={method: summarize(rows, [s["id"] for s in manifest["samples"]])},
                      message_report_sha256_list=[digest(p) for p in reports])
    else:
        result["message_report_sha256"] = digest(args.report)
    result["manifest_sha256"] = fingerprint
    print(json.dumps(result, indent=2, allow_nan=False))
