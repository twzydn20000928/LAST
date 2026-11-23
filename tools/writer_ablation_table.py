"""Pool the frozen Hunyuan I2V equal-margin writer pairs using raw bit counts."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("minimum-margin", "fixed-target")
CONDITIONS = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")


def render(paths):
    plan = json.loads((ROOT / "configs/paper_subsets.json").read_bytes())["ablation_i2v_30"]
    seen = set()
    totals = Counter()
    quality = {v: [] for v in VARIANTS}
    protocol = None
    for path in paths:
        report = json.loads(path.read_bytes())
        sample = report["video_id"]
        if sample not in plan or sample in seen:
            raise ValueError(f"Unexpected or duplicate sample {sample}")
        seen.add(sample)
        if (report["family"], report["mode"], report["margin"]) != ("hunyuan", "i2v", 0.5):
            raise ValueError(f"Unexpected writer protocol for {sample}")
        signature = (report["settings"], report["quality_definition"])
        if protocol is not None and protocol != signature:
            raise ValueError("Generation settings or quality definitions differ across pairs")
        protocol = signature
        for variant in VARIANTS:
            result = report["variants"][variant]
            rows = result["conditions"]
            if sorted(r["condition"] for r in rows) != sorted(CONDITIONS):
                raise ValueError(f"Incomplete or duplicated conditions in {path}")
            for row in rows:
                k = row["correct_bits"]
                if type(k) is not int or not 0 <= k <= 512 or row["total_bits"] != 512:
                    raise ValueError(f"Invalid information-bit counts in {path}")
                totals[variant, row["condition"]] += k
            psnr, ssim = result["psnr_db"], result["ssim"]
            if psnr is None or not math.isfinite(psnr) or not -1 <= ssim <= 1:
                raise ValueError(f"Expected finite per-video fidelity measurements in {path}")
            quality[variant].append((psnr, ssim))
    if not seen:
        raise ValueError("Supply at least one audited writer pair")
    bits = 512 * len(seen)
    print(f"{len(seen)}/{len(plan)} matched videos; {bits} information bits per condition.")
    print("\n| Condition | Minimum margin (%) | Fixed target (%) | Difference (pp) |")
    print("|---|---:|---:|---:|")
    for condition in CONDITIONS:
        a, b = (100 * totals[v, condition] / bits for v in VARIANTS)
        print(f"| {condition} | {a:.2f} | {b:.2f} | {a - b:+.2f} |")
    print("\n| Writer | Mean per-video PSNR (dB) | Mean SSIM |\n|---|---:|---:|")
    for variant, rows in quality.items():
        print(f"| {variant} | {mean(x for x, _ in rows):.3f} | {mean(y for _, y in rows):.5f} |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="*", type=Path)
    args = parser.parse_args()
    render(args.reports or sorted((ROOT / "results").glob("paired_writer_*.json")))
