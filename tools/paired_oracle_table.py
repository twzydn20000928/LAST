"""Compare a completed oracle run with the same video's audited blind reads."""
import argparse
import json
import re
from pathlib import Path

from last.report import CONDITIONS


def compare(report, oracle, video_id):
    blind = [row for row in report["audited_observations"] if row["video_id"] == video_id
             and (row["family"], row["mode"], row["method"], row["map_seed"]) == ("hunyuan", "i2v", "last", 0)]
    if oracle["status"] != "completed" or video_id not in report["sample_ids"]:
        raise ValueError("Expected a completed run and a declared primary sample")
    for rows in (blind, oracle["rows"]):
        if sorted(row["condition"] for row in rows) != sorted(CONDITIONS):
            raise ValueError("Expected one observation per primary condition")
        for row in rows:
            n = row["correct_bits"]
            if type(n) is not int or not 0 <= n <= 512 or row["total_bits"] != 512 or row["exact_message"] is not (n == 512):
                raise ValueError("Invalid information-bit measurement")
    reference = {row["condition"]: row for row in blind}
    pairs = []
    for row in oracle["rows"]:
        b = reference[row["condition"]]
        for field, expected in (("received_sha256", b["video_sha256"]), ("attack_receipt_sha256", b["receipt_sha256"])):
            if not re.fullmatch("[0-9a-f]{64}", expected) or row[field] != expected:
                raise ValueError(f"{video_id}/{row['condition']}: mismatched {field}")
        if b["status"] != "completed" or row["route"] != "oracle_attack_map":
            raise ValueError("Invalid reader status or route")
        pairs.append((row["condition"], b["correct_bits"], row["correct_bits"]))
    return pairs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--video-id", required=True)
    args = parser.parse_args()
    pairs = compare(json.loads(args.report.read_bytes()), json.loads(args.oracle.read_bytes()), args.video_id)
    print("| Condition | Blind correct / 512 | Oracle correct / 512 | Difference in correct bits |")
    print("|---|---:|---:|---:|")
    for condition, blind, oracle in pairs:
        print(f"| {condition} | {blind} | {oracle} | {oracle-blind:+d} |")
