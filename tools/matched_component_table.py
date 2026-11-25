"""Compare writer and reader ablations on a common verified full-LAST baseline."""
import json
from pathlib import Path
from statistics import mean

from reader_ablation_table import CONDITIONS, VARIANTS


def compare(reader, writers, plan):
    if reader["ordered_subset"] != plan or len(plan) != len(set(plan)):
        raise ValueError("Unexpected ablation subset")
    observed = {}
    for row in reader["observations"]:
        key = row["video_id"], row["condition"], row["variant"]
        if key in observed or key[0] not in plan or key[1] not in CONDITIONS or key[2] not in VARIANTS:
            raise ValueError("Unexpected reader observation")
        observed[key] = row
    accepted, excluded = [], {}
    totals = {v: dict.fromkeys(CONDITIONS, 0) for v in (*VARIANTS, "fixed-target")}
    seen = set()
    for writer in writers:
        video = writer["video_id"]
        if video not in plan or video in seen or (writer["family"], writer["mode"], writer["margin"]) != ("hunyuan", "i2v", 0.5):
            raise ValueError("Unexpected writer pair")
        seen.add(video)
        conditions = {}
        for variant in ("minimum-margin", "fixed-target"):
            rows = writer["variants"][variant]["conditions"]
            if sorted(r["condition"] for r in rows) != sorted(CONDITIONS):
                raise ValueError("Missing or repeated writer observation")
            for r in rows:
                conditions[variant, r["condition"]] = r
        mismatch = []
        for c in CONDITIONS:
            base = conditions["minimum-margin", c]
            group = [observed.get((video, c, v)) for v in VARIANTS]
            if any(r is None for r in group):
                mismatch.append(c)
                continue
            if len({r["received_sha256"] for r in group}) != 1:
                raise ValueError("Reader variants used different inputs")
            full = observed[video, c, "full"]
            if base["received_sha256"] != full["received_sha256"]:
                mismatch.append(c)
            elif base["correct_bits"] != full["correct_bits"]:
                raise ValueError("Full reader disagrees on identical MP4")
        if mismatch:
            excluded[video] = mismatch
            continue
        accepted.append(video)
        for c in CONDITIONS:
            for v in totals:
                r = conditions[v, c] if v == "fixed-target" else observed[video, c, v]
                n = r["correct_bits"]
                if type(n) is not int or not 0 <= n <= 512:
                    raise ValueError("Invalid 512-bit result")
                totals[v][c] += n
    if not accepted:
        raise ValueError("No verified shared baseline")
    return accepted, excluded, totals


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    results = root / "results"
    read = lambda path: json.loads(path.read_bytes())
    writers = [read(p) for p in sorted(results.glob("paired_writer_*.json"))]
    ids, skipped, counts = compare(read(results / "hunyuan_i2v_reader_ablation_first12.json"), writers,
                                   read(root / "configs/paper_subsets.json")["ablation_i2v_30"])
    print(f"Matched {len(ids)}/30 videos. Included: {', '.join(ids)}")
    print("Unmatched full baseline by condition:", json.dumps(skipped))
    print("| Variant | " + " | ".join(CONDITIONS) + " |")
    print("|---" + "|---:" * len(CONDITIONS) + "|")
    for v, values in counts.items():
        print("| " + v + " | " + " | ".join(f"{values[c]/(512*len(ids)):.2%}" for c in CONDITIONS) + " |")
    print("\n| Writer | Mean PSNR (dB) | Mean SSIM |\n|---|---:|---:|")
    for variant in ("minimum-margin", "fixed-target"):
        measurements = [w["variants"][variant] for w in writers if w["video_id"] in ids]
        print(f"| {variant} | {mean(r['psnr_db'] for r in measurements):.3f} | "
              f"{mean(r['ssim'] for r in measurements):.5f} |")
