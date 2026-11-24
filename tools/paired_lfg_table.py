"""Render a matched LAST/LFG comparison from published per-video counts."""
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


def main(samples=SAMPLES, report_path=None):
    if report_path is None:
        size = "seven" if len(samples) == 7 else "eight"
        report_path = RESULTS / f"hunyuan_i2v_last_lfg_first_{size}_paired.json"
    report = json.loads(report_path.read_bytes())
    full_report = samples is None
    if full_report:
        samples = report["sample_ids"]
    if not samples or len(set(samples)) != len(samples):
        raise ValueError("Expected distinct matched sample IDs")
    counts = {}
    pipelines = set()
    rows = report["audited_observations"] if "audited_observations" in report else report["observations"]
    for row in rows:
        if row["video_id"] not in samples:
            if full_report:
                raise ValueError("Observation refers to a sample outside the report manifest")
            continue
        key = row["video_id"], row["condition"], row["method"]
        if key in counts or row["status"] != "completed":
            raise ValueError(f"Duplicate or incomplete observation for {key}")
        counts[key] = count_bits(row)
        pipelines.add((row["family"], row["mode"]))
    expected = {(s, c, m) for s in samples for c in CONDITIONS for m in ("last", "lfg")}
    if len(pipelines) != 1 or set(counts) != expected:
        raise ValueError("Expected both methods and all seven conditions on the same pipeline")
    lines = ["| Condition | LAST correct bits | LFG correct bits | LAST bit accuracy | LFG bit accuracy | LAST exact | LFG exact |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        a = [counts[sample, condition, "last"] for sample in samples]
        b = [counts[sample, condition, "lfg"] for sample in samples]
        total = 512 * len(samples)
        lines.append(f"| {condition} | {sum(a)}/{total} | {sum(b)}/{total} | "
                     f"{100 * sum(a) / total:.2f}% | {100 * sum(b) / total:.2f}% | "
                     f"{a.count(512)}/{len(a)} | {b.count(512)}/{len(b)} |")
    print("\n".join(lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--samples", type=int, choices=(3, 7, 8))
    inputs.add_argument("--report", type=Path, help="Print all sample IDs in a published matched report")
    args = parser.parse_args()
    if args.report:
        main(None, args.report)
    else:
        main(tuple(f"paper-{i:03d}" for i in range(args.samples or 3)))
