"""Render paired information-bit accuracy from the published reader ablation."""
import argparse
import json
from pathlib import Path

CONDITIONS = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")
VARIANTS = ("full", "without_cgc", "without_sws", "without_ccta")
DEFAULT = Path(__file__).resolve().parents[1] / "results/hunyuan_i2v_reader_ablation_interim.json"


def render(report):
    frozen = json.loads((DEFAULT.parents[1] / "configs/paper_subsets.json").read_bytes())
    if report["ordered_subset"] != frozen["ablation_i2v_30"]:
        raise ValueError("Reader ablation sample list differs from the frozen Hunyuan I2V subset")
    planned = set(report["ordered_subset"])
    if len(planned) != report["planned_videos"] or len(planned) != len(report["ordered_subset"]):
        raise ValueError("Inconsistent planned subset")
    cells = {(c, v): {} for c in CONDITIONS for v in VARIANTS}
    for row in report["observations"]:
        sample, bits = row["video_id"], row["correct_bits"]
        cell = cells[row["condition"], row["variant"]]
        if sample not in planned or sample in cell or type(bits) is not int or not 0 <= bits <= 512:
            raise ValueError("Invalid or duplicate observation")
        cell[sample] = bits
    samples = set(cells["clean", "full"])
    if not samples or any(set(cell) != samples for cell in cells.values()):
        raise ValueError("Matched videos required across all variants and conditions")
    totals = {(c, v): sum(cell.values()) for (c, v), cell in cells.items()}
    recorded = {(r["condition"], r["variant"]): (r["correct_bits"], r["total_bits"]) for r in report["cells"]}
    denominator = len(samples) * 512
    if len(report["cells"]) != len(cells) or recorded != {key: (n, denominator) for key, n in totals.items()}:
        raise ValueError("Observation counts differ from aggregate cells")
    print(f"{len(samples)}/{len(planned)} paired videos. Bit accuracy (%), {denominator} bits per cell.\n")
    print("| Variant | " + " | ".join(CONDITIONS) + " |")
    print("|---|" + "---:|" * len(CONDITIONS))
    for v in VARIANTS:
        print("| " + v + " | " + " | ".join(f"{100 * totals[c, v] / denominator:.2f}" for c in CONDITIONS) + " |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT)
    render(json.loads(parser.parse_args().report.read_bytes()))
