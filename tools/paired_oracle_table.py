"""Compare a completed oracle run with the same video's audited blind reads."""
import argparse
import json
import re
from pathlib import Path

from last.report import CONDITIONS

# The frozen oracle_reader.py has two byte fingerprints across Git line endings.
FROZEN_ORACLE_HASHES = {
    "807f5a63030a286083504fd26a7f4267abd160014d81e151740a99a24bf1f73e",
    "409645be7cb9209cdc8217242bf1ef2858a40538a83a9755eb21b064fd9e5df0",
}


def compare(report, oracle, video_id):
    if oracle.get("source_sha256") not in FROZEN_ORACLE_HASHES:
        raise ValueError(f"{video_id}: unrecognized oracle reader source")
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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--oracle", type=Path)
    source.add_argument("--oracle-dir", type=Path, help="Directory containing a receipt for every sample ID in the report")
    parser.add_argument("--video-id")
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    if args.oracle_dir:
        if args.video_id:
            parser.error("--video-id applies to a single --oracle")
        ids = report["sample_ids"]
        if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r"paper-[0-9]{3}", s) for s in ids):
            raise ValueError("Expected unique primary sample IDs")
        results = {c: [] for c in CONDITIONS}
        for s in ids:
            path = args.oracle_dir / ("hunyuan_i2v_oracle_" + s.replace("-", "") + ".json")
            for c, b, o in compare(report, json.loads(path.read_bytes()), s):
                results[c].append((b, o))
        print(f"{len(ids)} paired Hunyuan I2V videos; {512*len(ids)} information bits per condition.")
        print("| Condition | Blind bits | Oracle bits | Both exact | Blind only | Oracle only | Neither exact |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        for c, pairs in results.items():
            counts = [sum((b == 512, o == 512) == outcome for b, o in pairs)
                      for outcome in ((True, True), (True, False), (False, True), (False, False))]
            values = [sum(b for b, _ in pairs), sum(o for _, o in pairs), *counts]
            print("| " + " | ".join([c, *map(str, values)]) + " |")
        raise SystemExit(0)
    if not args.video_id:
        parser.error("--oracle requires --video-id")
    pairs = compare(report, json.loads(args.oracle.read_bytes()), args.video_id)
    print("| Condition | Blind correct / 512 | Oracle correct / 512 | Difference in correct bits |")
    print("|---|---:|---:|---:|")
    for condition, blind, oracle in pairs:
        print(f"| {condition} | {blind} | {oracle} | {oracle-blind:+d} |")
