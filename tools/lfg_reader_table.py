"""Render the LFG reader rows of supplement Table 12 from public paired counts."""
import argparse
import json
import math
import statistics
from pathlib import Path

from last.report import CONDITIONS


def paired_psnr(fidelity, ids, cells, manifest_hash):
    if (fidelity["family"], fidelity["mode"], fidelity["manifest_sha256"]) != ("hunyuan", "i2v", manifest_hash):
        raise ValueError("Fidelity pipeline or manifest differs")
    selected = [r for r in fidelity["observations"]["lfg"] if r["video_id"] in ids]
    if len(selected) != len(ids) or {r["video_id"] for r in selected} != set(ids):
        raise ValueError("Missing or duplicated LFG fidelity pair")
    values = []
    for row in selected:
        if row["marked_sha256"] != cells[row["video_id"], "clean"]["received_sha256"]:
            raise ValueError("Quality was measured on a different marked video")
        mse = row["rgb_mse"]
        if mse == 0 and row["identical"] and row["psnr_db"] is None:
            values.append(math.inf)
        elif (0 < mse <= 1 and not row["identical"] and row["psnr_db"] is not None
              and math.isclose(row["psnr_db"], -10 * math.log10(mse), abs_tol=1e-7)):
            values.append(row["psnr_db"])
        else:
            raise ValueError("Invalid PSNR for reported RGB error")
    return statistics.mean(values)


def render(report, fidelity=None, all_conditions=False):
    ids = report["sample_ids"]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Expected distinct paired sample IDs")
    rows = report["observations"]
    cells = {(r["video_id"], r["condition"]): r for r in rows}
    if len(cells) != len(rows) or set(cells) != {(v, c) for v in ids for c in CONDITIONS}:
        raise ValueError("Expected one observation per sample and condition")
    for row in rows:
        if row["total_bits"] != 512 or any(type(row[k]) is not int or not 0 <= row[k] <= 512
                                            for k in ("original_bits", "ccta_bits")):
            raise ValueError("Invalid 512-bit observation")
    print(f"Hunyuan I2V paired videos: {len(ids)}/400")
    psnr = paired_psnr(fidelity, ids, cells, report["manifest_sha256"]) if fidelity else None
    print("| Reader | Clean exact | Drop bit accuracy | Drop exact | Compression exact |" +
          (" Mean PSNR (dB) |" if fidelity else ""))
    print("|---|---:|---:|---:|---:|" + ("---:|" if fidelity else ""))
    for label, key in [("Original LFG", "original_bits"), ("LFG + CCTA", "ccta_bits")]:
        def exact(condition):
            return sum(cells[v, condition][key] == 512 for v in ids)
        correct = sum(cells[v, "drop"][key] for v in ids)
        n = len(ids)
        print(f"| {label} | {exact('clean')}/{n} | {correct}/{512*n} "
              f"({correct/(512*n):.2%}) | {exact('drop')}/{n} | {exact('compression')}/{n} |" +
              (f" {psnr:.2f} |" if fidelity else ""))
    if all_conditions:
        print("\n| Condition | Original LFG bits | LFG + CCTA bits |")
        print("|---|---:|---:|")
        total = 512 * len(ids)
        for condition in CONDITIONS:
            counts = [sum(cells[v, condition][key] for v in ids)
                      for key in ("original_bits", "ccta_bits")]
            values = [f"{count}/{total} ({count / total:.2%})" for count in counts]
            print(f"| {condition} | {values[0]} | {values[1]} |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--all-conditions", action="store_true", help="Also show bit counts and accuracy for every attack")
    parser.add_argument("--fidelity", type=Path, help="Matched primary fidelity report for the same marked MP4s")
    args = parser.parse_args()
    render(json.loads(args.report.read_bytes()), json.loads(args.fidelity.read_bytes()) if args.fidelity else None,
           args.all_conditions)
