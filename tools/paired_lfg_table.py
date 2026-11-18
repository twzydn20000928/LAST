"""Render the three-case Hunyuan I2V comparison from published per-video counts."""
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


def main():
    last = json.loads((RESULTS / "last_hunyuan_i2v_audited_partial.json").read_bytes())
    lfg = json.loads((RESULTS / "lfg_hunyuan_i2v_three_cases.json").read_bytes())
    counts = {}
    for row in last["audited_observations"]:
        if row["video_id"] not in SAMPLES or row["condition"] not in CONDITIONS:
            continue
        key = (row["video_id"], row["condition"])
        if key in counts or (row["family"], row["mode"], row["method"], row["status"]) != (
            "hunyuan", "i2v", "last", "completed"
        ):
            raise ValueError(f"Unexpected or duplicate LAST observation for {key}")
        counts[key] = count_bits(row)

    lines = ["| Condition | LAST correct bits | LFG correct bits | LAST exact | LFG exact |",
             "|---|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        a = [counts[sample, condition] for sample in SAMPLES]
        b = [count_bits(lfg["cases"][sample]["conditions"][condition]) for sample in SAMPLES]
        total = 512 * len(SAMPLES)
        lines.append(f"| {condition} | {sum(a)}/{total} | {sum(b)}/{total} | "
                     f"{a.count(512)}/{len(a)} | {b.count(512)}/{len(b)} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
