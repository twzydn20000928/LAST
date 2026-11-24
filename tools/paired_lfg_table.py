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


def main(samples=SAMPLES, report_path=None, additional_reports=()):
    if report_path is None:
        size = "seven" if len(samples) == 7 else "eight"
        report_path = RESULTS / f"hunyuan_i2v_last_lfg_first_{size}_paired.json"
    report = json.loads(report_path.read_bytes())
    full_report = samples is None
    rows = []
    if full_report:
        samples = []
    if additional_reports and not full_report:
        raise ValueError("Combining reports requires full slices")
    for part in [report, *(json.loads(path.read_bytes()) for path in additional_reports)]:
        if part["manifest_sha256"] != report["manifest_sha256"]:
            raise ValueError("Combining reports requires full slices from the same manifest")
        part_rows = part.get("audited_observations", part.get("observations", []))
        if full_report:
            declared = part["sample_ids"]
            if not declared or {r["video_id"] for r in part_rows} != set(declared):
                raise ValueError("Slice observations disagree with declared sample IDs")
            samples.extend(declared)
        rows.extend(part_rows)
    if not samples or len(set(samples)) != len(samples):
        raise ValueError("Expected distinct matched sample IDs")
    counts = {}
    pipelines = set()
    for row in rows:
        if row["video_id"] not in samples:
            if full_report:
                raise ValueError("Observation refers to a sample outside the report manifest")
            continue
        key = row["video_id"], row["condition"], row["method"]
        if key in counts or row["status"] != "completed":
            raise ValueError(f"Duplicate or incomplete observation for {key}")
        if row["map_seed"] != 0:
            raise ValueError(f"Unexpected primary attack map seed for {key}")
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
    inputs.add_argument("--report", type=Path, nargs="+", help="One or more disjoint matched reports")
    args = parser.parse_args()
    if args.report:
        main(None, args.report[0], args.report[1:])
    else:
        main(tuple(f"paper-{i:03d}" for i in range(args.samples or 3)))
