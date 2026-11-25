"""Summarize the primary and uniform-profile arms of supplementary Table 16."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean

from last.cluster_intervals import summarize
from last.data import validate


def collect(manifest, reports):
    validate(manifest)
    samples = {s["id"]: s for s in manifest["samples"]}
    labels = ("nonuniform-profile", "uniform-profile")
    drops = {name: [] for name in labels}
    quality = {name: [] for name in labels}
    seen = set()
    settings = None
    for report in reports:
        video = report["video_id"]
        if (video in seen or video not in samples or report["seed"] != samples[video]["seed"]
                or (report["family"], report["mode"], report["margin"]) != ("hunyuan", "i2v", 0.5)
                or set(report["variants"]) != set(labels)):
            raise ValueError("Unexpected profile intervention or sample")
        seen.add(video)
        signature = (report["settings"], report["quality_definition"])
        if settings is not None and settings != signature:
            raise ValueError("Mixed generation or fidelity protocols")
        settings = signature
        for name in labels:
            arm = report["variants"][name]
            row, = [r for r in arm["conditions"] if r["condition"] == "drop"]
            bits = row["correct_bits"]
            if (type(bits) is not int or not 0 <= bits <= 512 or row["total_bits"] != 512
                    or row["exact_message"] is not (bits == 512) or not math.isfinite(arm["psnr_db"])
                    or not -1 <= arm["ssim"] <= 1):
                raise ValueError("Invalid deletion or fidelity observation")
            drops[name].append(dict(row, video_id=video, map_seed=0, status="completed"))
            quality[name].append((arm["psnr_db"], arm["ssim"]))
    if not seen:
        raise ValueError("Supply at least one measured pair")
    result = dict(completed=len(seen), planned=len(samples), arms={}, paired_mrr_ci95=None)
    for name in labels:
        rows = drops[name]
        result["arms"][name] = dict(correct_bits=sum(r["correct_bits"] for r in rows),
                                    total_bits=512*len(rows), exact_messages=sum(r["exact_message"] for r in rows),
                                    bit_accuracy=mean(r["correct_bits"]/512 for r in rows),
                                    message_recovery=mean(r["exact_message"] for r in rows),
                                    psnr_db=mean(p for p, _ in quality[name]), ssim=mean(s for _, s in quality[name]))
    if seen == set(samples):
        clusters = {video: row["prompt"].strip() for video, row in samples.items()}
        delta = summarize(drops["uniform-profile"], clusters, (0,), drops["nonuniform-profile"])
        result["paired_mrr_ci95"] = delta["message_recovery_ci95"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(json.loads(args.manifest.read_bytes()), [json.loads(p.read_bytes()) for p in args.reports]),
                     indent=2, allow_nan=False))
