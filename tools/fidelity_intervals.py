"""Compute supplementary PSNR and SSIM intervals from paired-reference measurements."""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from last.cluster_intervals import cluster_mean_interval
from last.data import validate


def collect(manifest_bytes, report, method):
    manifest = json.loads(manifest_bytes)
    validate(manifest)
    prompts = {s["id"]: s["prompt"].strip() for s in manifest["samples"]}
    ids = report["sample_ids"]
    rows = report["observations"][method]
    if (report["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()
            or not ids or len(set(ids)) != len(ids) or not set(ids) <= prompts.keys()
            or sorted(r["video_id"] for r in rows) != sorted(ids)):
        raise ValueError("Measurements do not match the declared manifest and videos")
    groups = defaultdict(list)
    for row in rows:
        mse, psnr, ssim = row["rgb_mse"], row["psnr_db"], row["ssim"]
        if (row["identical"] or row["frames"] != 65 or not 0 < mse <= 1 or psnr is None
                or not math.isclose(psnr, -10*math.log10(mse), abs_tol=1e-8) or not -1 <= ssim <= 1):
            raise ValueError("Expected finite per-video fidelity measurements")
        groups[prompts[row["video_id"]]].append((psnr, ssim))
    clusters = [groups[prompt] for prompt in sorted(groups)]
    means, ci = cluster_mean_interval([np.sum(c, axis=0) for c in clusters], [len(c) for c in clusters])
    return dict(family=report["family"], mode=report["mode"], method=method, videos=len(ids),
                planned=len(prompts), prompt_clusters=len(groups), draws=10000, seed=0,
                psnr_db=means[0], psnr_ci95=ci[0] if ci else None,
                ssim=means[1], ssim_ci95=ci[1] if ci else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--method", choices=("last", "lfg"), default="last")
    args = parser.parse_args()
    print(json.dumps(collect(args.manifest.read_bytes(), json.loads(args.report.read_bytes()), args.method),
                     indent=2, allow_nan=False))
