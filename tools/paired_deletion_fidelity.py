"""Summarize random-deletion recovery and paired-reference fidelity on the same videos."""
import argparse
import json
from pathlib import Path

from last.fidelity_summary import summarize
from last.report import completed_bit_counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", nargs=2, action="append", type=Path, required=True,
                        metavar=("ATTACK_REPORT", "FIDELITY_REPORT"))
    args = parser.parse_args()
    pipeline = None
    methods = ("last", "lfg")
    samples = []
    observations = {method: [] for method in methods}
    deletion = {method: [] for method in methods}
    same_reference = 0
    for attack_path, quality_path in args.pair:
        attacks = json.loads(attack_path.read_bytes())
        quality = json.loads(quality_path.read_bytes())
        group = (quality["family"], quality["mode"], quality["manifest_sha256"])
        if pipeline is None:
            pipeline = group
        ids = attacks["sample_ids"]
        if (group != pipeline or not attacks["complete"] or not attacks["artifact_verification"]
                or attacks["manifest_sha256"] != group[2] or ids != quality["sample_ids"]
                or not ids or len(set(ids)) != len(ids) or set(ids).intersection(samples)):
            raise ValueError("Require verified, disjoint sample IDs from the same pipeline and manifest")
        samples.extend(ids)
        references = {}
        for method in methods:
            quality_rows = quality["observations"][method]
            by_id = {r["video_id"]: r for r in quality_rows}
            if set(by_id) != set(ids) or len(quality_rows) != len(ids):
                raise ValueError("Missing or duplicate fidelity observations")
            for condition in ("clean", "drop"):
                rows = [r for r in attacks["audited_observations"]
                        if r["method"] == method and r["condition"] == condition]
                if len(rows) != len(ids) or {r["video_id"] for r in rows} != set(ids):
                    raise ValueError("Missing or duplicate attack observations")
                for r in rows:
                    if ((r["family"], r["mode"]) != pipeline[:2] or r["status"] != "completed"
                            or r["map_seed"] != 0):
                        raise ValueError("Attack condition differs from the primary protocol")
                    if condition == "clean":
                        if r["video_sha256"] != by_id[r["video_id"]]["marked_sha256"]:
                            raise ValueError("Fidelity and robustness use different marked videos")
                    else:
                        deletion[method].append(completed_bit_counts(r))
            observations[method].extend(quality_rows)
            references[method] = [by_id[i]["reference_sha256"] for i in ids]
        same_reference += sum(a == b for a, b in zip(references["last"], references["lfg"]))
    print(f"{pipeline[0]} {pipeline[1]}, {len(samples)} paired cases. "
          f"Byte-identical unmarked references across methods: {same_reference}/{len(samples)}.\n")
    print("| Method | Mean video PSNR (dB) | Mean SSIM | Drop: correct bits | Drop: exact messages |")
    print("|---|---:|---:|---:|---:|")
    for method in methods:
        fidelity = summarize(observations[method], samples)
        psnr = fidelity["observed_mean_video_psnr_db"]
        formatted = "inf" if fidelity["observed_mean_video_psnr_is_infinite"] else f"{psnr:.2f}"
        counts = deletion[method]
        print(f"| {method} | {formatted} | {fidelity['observed_mean_ssim']:.4f} | "
              f"{sum(c for c, _ in counts)}/{sum(n for _, n in counts)} | "
              f"{sum(c == n for c, n in counts)}/{len(counts)} |")


if __name__ == "__main__":
    main()
