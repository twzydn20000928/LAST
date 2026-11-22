"""Render the paired Hunyuan I2V comparison from published per-video counts."""
import json
from pathlib import Path


RESULTS = Path(__file__).resolve().parents[1] / "results"
SAMPLES = ("paper-000", "paper-001", "paper-002")
CONDITIONS = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")


def count_bits(row):
    correct = row["correct_bits"]
    if type(correct) is not int or row["total_bits"] != 512 or not 0 <= correct <= 512:
        raise ValueError("Expected a completed 512-information-bit measurement")
    return correct


def main(samples=SAMPLES):
    report = json.loads((RESULTS / "hunyuan_i2v_last_lfg_first_seven_paired.json").read_bytes())
    counts = {}
    for row in report["observations"]:
        if row["video_id"] not in samples:
            continue
        key = row["video_id"], row["condition"], row["method"]
        if key in counts or row["status"] != "completed":
            raise ValueError(f"Duplicate or incomplete observation for {key}")
        counts[key] = count_bits(row)
    lines = ["| Condition | LAST correct bits | LFG correct bits | LAST exact | LFG exact |",
             "|---|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        a = [counts[sample, condition, "last"] for sample in samples]
        b = [counts[sample, condition, "lfg"] for sample in samples]
        total = 512 * len(samples)
        lines.append(f"| {condition} | {sum(a)}/{total} | {sum(b)}/{total} | "
                     f"{a.count(512)}/{len(a)} | {b.count(512)}/{len(b)} |")
    print("\n".join(lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, choices=(3, 7), default=3)
    args = parser.parse_args()
    main(tuple(f"paper-{i:03d}" for i in range(args.samples)))
