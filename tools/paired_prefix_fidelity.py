"""Audit paired fidelity on the exact samples in an audited LAST/LFG attack report."""
import argparse
import hashlib
import json
from pathlib import Path

from last.fidelity_summary import summarize


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(report, root):
    samples = report["sample_ids"]
    rows = [r for r in report["audited_observations"] if r["condition"] == "clean"]
    if not report["complete"] or len({(r["family"], r["mode"]) for r in rows}) != 1:
        raise ValueError("Require a completed paired prefix from one generation pipeline")
    observations = {"last": [], "lfg": []}
    for r in rows:
        folder = root / r["run"]
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unexpected run path")
        campaign = json.loads((folder / "campaign.json").read_bytes())
        generation = json.loads((folder / "receipt.json").read_bytes())
        if (campaign["status"] != "completed" or campaign["plan_sha256"] != report["plan_sha256"]
                or any(campaign["item"][k] != r[k] for k in ("video_id", "family", "mode", "method"))
                or generation["status"] != "completed" or generation["method"] != r["method"]):
            raise ValueError("Generation or campaign differs from paired measurement")
        path = folder / "quality.json"
        quality = json.loads(path.read_bytes())
        for name in ("marked", "reference"):
            if digest(folder / (name + ".mp4")) != quality[name + "_sha256"]:
                raise ValueError("Fidelity input differs from scored MP4")
        if generation["marked_sha256"] != quality["marked_sha256"] or r["video_sha256"] != quality["marked_sha256"]:
            raise ValueError("Robustness and fidelity refer to different watermarked videos")
        keys = ("definition", "frames", "rgb_mse", "ssim", "psnr_db", "identical", "marked_sha256", "reference_sha256")
        observations[r["method"]].append(dict(video_id=r["video_id"], quality_receipt_sha256=digest(path),
                                              **{k: quality[k] for k in keys}))
    cells = {m: summarize(items, samples) for m, items in observations.items()}
    if not all(cell["complete"] for cell in cells.values()):
        raise ValueError("Missing quality pair")
    refs = {m: {r["video_id"]: r["reference_sha256"] for r in items} for m, items in observations.items()}
    return dict(family=rows[0]["family"], mode=rows[0]["mode"], sample_ids=samples,
                plan_sha256=report["plan_sha256"], manifest_sha256=report["manifest_sha256"],
                identical_reference_files=sum(refs["last"][s] == refs["lfg"][s] for s in samples),
                observations=observations, cells=cells, scope="Paired prefix; each method uses its own reference")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.report.read_bytes()), args.root), indent=2, allow_nan=False))
