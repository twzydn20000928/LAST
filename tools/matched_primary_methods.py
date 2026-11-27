"""Compare primary methods on the common sample IDs for each condition."""
import argparse
import hashlib
import json
from pathlib import Path

from last.report import CONDITIONS
from last.robustness_table import collect


def render(reports, manifest, family, mode, methods, first=None):
    if len(methods) < 2 or len(set(methods)) != len(methods):
        raise ValueError("Supply at least two distinct methods")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    ordered_ids = [s["id"] for s in json.loads(manifest.read_bytes())["samples"]]
    valid_ids = set(ordered_ids)
    if first is not None and not 1 <= first <= len(ordered_ids):
        raise ValueError("Prefix size must be within the frozen manifest")
    rows = {m: {c: {} for c in CONDITIONS} for m in methods}
    for path in reports:
        report = json.loads(path.read_bytes())
        if report.get("manifest_sha256") != digest or "audited_observations" not in report:
            raise ValueError(f"Expected an audited report from the supplied manifest: {path}")
        collect([report])
        for r in report["audited_observations"]:
            method = r["method"]
            if (r["family"], r["mode"]) != (family, mode) or method not in rows:
                continue
            cell = rows[method][r["condition"]]
            video = r["video_id"]
            if video not in valid_ids or video in cell:
                raise ValueError(f"Unknown or duplicate sample {method}/{video}/{r['condition']}")
            cell[video] = r["correct_bits"]
    if any(not any(cells.values()) for cells in rows.values()):
        raise ValueError("A requested method has no verified observations for this pipeline")
    if first is not None:
        prefix = ordered_ids[:first]
        for method, cells in rows.items():
            for condition, observations in cells.items():
                missing = set(prefix) - observations.keys()
                if missing:
                    raise ValueError(f"Missing frozen sample(s) for {method}/{condition}: {sorted(missing)}")
    print("| Condition | Common samples | " + " | ".join(methods) + " |")
    print("|---|---|" + "---:|" * len(methods))
    for cond in CONDITIONS:
        ids = prefix if first is not None else sorted(set.intersection(*(set(rows[m][cond]) for m in methods)))
        values = []
        for method in methods:
            bits = [rows[method][cond][i] for i in ids]
            values.append(f"{sum(bits)}/{512 * len(bits)} ({bits.count(512)}/{len(bits)})" if bits else "—")
        print("| " + " | ".join([cond, ", ".join(ids) or "—", *values]) + " |")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reports", nargs="+", type=Path, required=True)
    p.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    p.add_argument("--family", required=True, choices=("hunyuan", "wan22"))
    p.add_argument("--mode", required=True, choices=("i2v", "t2v"))
    p.add_argument("--methods", nargs="+", required=True)
    p.add_argument("--first", type=int, help="Require all seven conditions for the first N manifest samples")
    a = p.parse_args()
    render(a.reports, a.manifest, a.family, a.mode, a.methods, a.first)
