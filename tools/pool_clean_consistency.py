"""Pool clean consistency scores on the frozen component subset."""
import argparse
import json
import math
from pathlib import Path

from last.hypothesis_statistics import matched_summary


def pool(reports, planned):
    seen = set()
    positive, negative, ids = [], [], []
    energy_values = {name: ([], []) for name in ("raw", "calibrated")}
    calibration_ids = set()
    assignments = {(i, j) for i in range(13) for j in range(13) if i != j}
    for report in reports:
        video = report["video_id"]
        if (video not in planned or video in seen
                or (report["family"], report["mode"], report["method"]) != ("hunyuan", "i2v", "last")):
            raise ValueError(f"Unexpected or repeated component video: {video}")
        seen.add(video)
        rows = report["pairs"]
        observed = {(r["window_start"], r["wrong_group_start"]) for r in rows}
        if len(rows) != len(assignments) or observed != assignments:
            raise ValueError(f"Incomplete or duplicated four-group comparison: {video}")
        energy = {}
        calibration = report.get("calibration_sha256")
        calibration_ids.add(calibration)
        if len(calibration_ids) > 1:
            raise ValueError("All reports must use the same calibration or all omit energy")
        if "energy_pairs" in report or calibration is not None:
            if not isinstance(calibration, str) or len(calibration) != 64 or any(
                    c not in "0123456789abcdef" for c in calibration):
                raise ValueError("Missing or invalid calibration digest")
            energy_rows = report["energy_pairs"]
            energy = {(r["window_start"], r["wrong_group_start"]): r for r in energy_rows}
            if set(energy) != assignments or len(energy_rows) != len(assignments):
                raise ValueError("Energy scores must cover the same window assignments as consistency")
        correct_by_start = {}
        for r in rows:
            i, j = r["window_start"], r["wrong_group_start"]
            correct, wrong = r["correct"], r["wrong"]
            if not all(math.isfinite(s) and abs(s) <= 1 + 1e-12 for s in (correct, wrong)):
                raise ValueError("Invalid cosine score")
            if correct_by_start.setdefault(i, correct) != correct:
                raise ValueError("Correct score changed for the same four windows")
            ids.append(f"{video}/{i}/{j}")
            positive.append(correct)
            negative.append(wrong)
            if energy:
                for name, (pos, neg) in energy_values.items():
                    pos.append(energy[i, j][name + "_correct"])
                    neg.append(energy[i, j][name + "_wrong"])
    result = dict(planned_videos=len(planned), observed_videos=len(seen),
                missing_ids=[v for v in planned if v not in seen],
                summary=matched_summary(positive, negative, ids, ids))
    if energy_values["raw"][0]:
        result["calibration_sha256"] = calibration_ids.pop()
        result["energy_summary"] = {k: matched_summary(pos, neg, ids, ids)
                                    for k, (pos, neg) in energy_values.items()}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    manifest = Path(__file__).resolve().parents[1] / "configs/paper_subsets.json"
    planned = json.loads(manifest.read_bytes())["ablation_i2v_30"]
    print(json.dumps(pool([json.loads(p.read_bytes()) for p in args.reports], planned),
                     indent=2, allow_nan=False))
