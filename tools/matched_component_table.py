"""Compare writer and reader ablations on a common verified full-LAST baseline."""
import argparse
import json
from pathlib import Path
from statistics import mean, median

from reader_ablation_table import CONDITIONS, VARIANTS
from writer_ablation_table import validated_bits


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
    protocol = None
    for writer in writers:
        video = writer["video_id"]
        if video not in plan or video in seen or (writer["family"], writer["mode"], writer["margin"]) != ("hunyuan", "i2v", 0.5):
            raise ValueError("Unexpected writer pair")
        signature = writer["settings"], writer["quality_definition"]
        if protocol is not None and signature != protocol:
            raise ValueError("Generation settings or quality definitions differ across writer pairs")
        protocol = signature
        seen.add(video)
        conditions = {}
        for variant in ("minimum-margin", "fixed-target"):
            rows = writer["variants"][variant]["conditions"]
            if sorted(r["condition"] for r in rows) != sorted(CONDITIONS):
                raise ValueError("Missing or repeated writer observation")
            for r in rows:
                validated_bits(r)
                if r["condition"] == "clean" and r["received_sha256"] != writer["variants"][variant]["marked_sha256"]:
                    raise ValueError(f"Clean writer observation differs from marked MP4: {video}/{variant}")
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


def use_archived_reread(reader, reread, writers):
    """Replace complete cases only when the original full-reader input differed."""
    plan = reader["ordered_subset"]
    if reread["ordered_subset"] != plan:
        raise ValueError("Reader rerun uses a different plan")
    rows = reread["observations"]
    ids = {r["video_id"] for r in rows}
    pairs = [w for w in writers if w["video_id"] in ids]
    if not ids or {w["video_id"] for w in pairs} != ids:
        raise ValueError("Every rerun requires its paired writer")
    original = {(r["video_id"], r["condition"]): r["received_sha256"]
                for r in reader["observations"] if r["variant"] == "full"}
    for w in pairs:
        video = w["video_id"]
        baseline = w["variants"]["minimum-margin"]["conditions"]
        hashes = [original[video, r["condition"]] for r in baseline]
        if hashes == [r["received_sha256"] for r in baseline]:
            raise ValueError(f"Original reader already used the archived inputs: {video}")
    matched, excluded, _ = compare(reread, pairs, plan)
    if set(matched) != ids or excluded:
        raise ValueError("Archived reader rerun is incomplete or uses different inputs")
    retained = [r for r in reader["observations"] if r["video_id"] not in ids]
    return dict(reader, observations=retained + rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    results = root / "results"
    read = lambda path: json.loads(path.read_bytes())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archived-reread", type=Path,
                        help="Paired reader report measured on archived writer MP4s")
    parser.add_argument("--reader", type=Path, default=results / "hunyuan_i2v_reader_ablation_14.json")
    parser.add_argument("--writers", type=Path, nargs="+", help="Paired writer JSON reports, one per video")
    parser.add_argument("--table4", action="store_true",
                        help="Render the manuscript's row order and 0–1 bit accuracies to three decimal places")
    parser.add_argument("--paired-condition", choices=CONDITIONS,
                        help="Also show the distribution of per-video full-minus-ablation bit gains")
    args = parser.parse_args()
    writers = [read(p) for p in (args.writers or sorted(results.glob("paired_writer_*.json")))]
    reader = read(args.reader)
    if args.archived_reread:
        reader = use_archived_reread(reader, read(args.archived_reread), writers)
    ids, skipped, counts = compare(reader, writers,
                                   read(root / "configs/paper_subsets.json")["ablation_i2v_30"])
    if args.table4:
        print("# Component ablation on matched Hunyuan image-to-video samples\n")
        print("Values are information-bit accuracies. The w/o MM variant replaces the minimum-margin write with fixed targets. "
              "The three reader ablations remove cross-group consistency (CGC), sliding-window search (SWS), "
              "or the entire temporal alignment module (CCTA), respectively.\n")
    print(f"Matched {len(ids)}/30 videos. Included: {', '.join(ids)}")
    writer_ids = {w["video_id"] for w in writers}
    reader_ids = {row["video_id"] for row in reader["observations"]}
    plan = reader["ordered_subset"]
    print("Reader observations available, writer pair missing:",
          json.dumps([v for v in plan if v in reader_ids and v not in writer_ids]))
    print("No writer pair or reader observations supplied:",
          json.dumps([v for v in plan if v not in reader_ids and v not in writer_ids]))
    print("Unmatched full baseline by condition:", json.dumps(skipped))
    print("| Variant | " + " | ".join(CONDITIONS) + " |")
    print("|---" + "|---:" * len(CONDITIONS) + "|")
    labels = {"full": "LAST", "fixed-target": "w/o MM", "without_cgc": "w/o CGC",
              "without_sws": "w/o SWS", "without_ccta": "w/o CCTA"}
    variants = labels if args.table4 else counts
    precision = ".3f" if args.table4 else ".2%"
    denominator = 512 * len(ids)
    for v in variants:
        cells = [format(counts[v][c] / denominator, precision) for c in CONDITIONS]
        print("| " + (labels[v] if args.table4 else v) + " | " + " | ".join(cells) + " |")
    if args.table4:
        print(f"\nCorrect information bits out of {denominator:,} per cell.\n")
        print("| Variant | " + " | ".join(CONDITIONS) + " |")
        print("|---" + "|---:" * len(CONDITIONS) + "|")
        for variant, label in labels.items():
            cells = [str(counts[variant][condition]) for condition in CONDITIONS]
            print("| " + " | ".join([label, *cells]) + " |")
    print("\n| Writer | Mean PSNR (dB) | Mean SSIM |\n|---|---:|---:|")
    for variant in ("minimum-margin", "fixed-target"):
        measurements = [w["variants"][variant] for w in writers if w["video_id"] in ids]
        print(f"| {variant} | {mean(r['psnr_db'] for r in measurements):.3f} | "
              f"{mean(r['ssim'] for r in measurements):.5f} |")

    if args.paired_condition:
        condition = args.paired_condition
        gains = {v: [] for v in labels if v != "full"}
        print(f"\nMinimum-margin minus fixed-target write on each matched video ({condition}).\n")
        print("| Video | PSNR difference (dB) | SSIM difference | Correct-bit difference |")
        print("|---|---:|---:|---:|")
        for writer in writers:
            if writer["video_id"] in ids:
                _, _, single = compare(reader, [writer], plan)
                for variant in gains:
                    gains[variant].append(single["full"][condition] - single[variant][condition])
                margin = writer["variants"]["minimum-margin"]
                fixed = writer["variants"]["fixed-target"]
                bit_delta = gains["fixed-target"][-1]
                print(f"| {writer['video_id']} | {margin['psnr_db'] - fixed['psnr_db']:+.3f} | "
                      f"{margin['ssim'] - fixed['ssim']:+.5f} | {bit_delta:+d} |")
        print(f"\nPer-video full LAST minus ablation, {condition}, in correct bits out of 512.\n")
        print("| Ablation | Full better | Tied | Full worse | Median gain | Total gain |")
        print("|---|---:|---:|---:|---:|---:|")
        for variant, delta in gains.items():
            assert sum(delta) == counts["full"][condition] - counts[variant][condition]
            print(f"| {labels[variant]} | {sum(d > 0 for d in delta)} | {delta.count(0)} | "
                  f"{sum(d < 0 for d in delta)} | {median(delta):g} | {sum(delta)} |")
