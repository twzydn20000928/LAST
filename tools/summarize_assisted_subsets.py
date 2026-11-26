"""Summarize matched intact/partial group reads from the released CPU recounts."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


def summarize(report, cases):
    rows = json.loads(report.read_bytes())
    paired = []
    draws = 0
    for index, row in enumerate(rows):
        video = f"paper-{index:03d}"
        case = (cases / f"hunyuan_i2v_last_controlled_paper{index:03d}.json").read_bytes()
        if row["video_id"] != video or row["case_sha256"] != hashlib.sha256(case).hexdigest():
            raise ValueError(f"Case fingerprint or prefix mismatch for {video}")
        record = json.loads(case)
        oracle, = [r for r in record["rows"] if (r["reader"], r["condition"]) == ("oracle", "drop")]
        subsets = row["subsets"]
        intact, partial = subsets["intact"], subsets["partial"]
        available, size = partial["groups"], intact["groups"]
        if (record["video_id"] != video or subsets["all"]["correct_bits"] != oracle["correct_bits"]
                or subsets["all"]["groups"] != available + size):
            raise ValueError(f"All-group read differs from controlled case for {video}")
        matched = row["partial_at_intact_count"]
        n = math.comb(available, size) if 0 < size <= available else 0
        total, exact = matched["sum_correct_bits"], matched["exact_messages"]
        if (matched["subsets"] != n or matched["group_count"] != size or not 0 <= exact <= n
                or not 512 * exact <= total <= 512 * n - (n - exact)):
            raise ValueError(f"Invalid equal-count recount for {video}")
        if n:
            if not 0 <= intact["correct_bits"] <= 512:
                raise ValueError(f"Invalid intact-group read for {video}")
            paired.append((intact["correct_bits"] / 512, total / (512 * n)))
            draws += n
    if not paired:
        raise ValueError("No eligible paired reads")
    return dict(videos=len(rows), eligible_videos=len(paired), partial_subsets=draws,
                intact_bit_accuracy=mean(x for x, _ in paired),
                matched_partial_bit_accuracy=mean(y for _, y in paired),
                videos_intact_higher=sum(x > y for x, y in paired))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--cases", type=Path, default=Path("results"))
    args = parser.parse_args()
    print(json.dumps(summarize(args.report, args.cases), indent=2))
