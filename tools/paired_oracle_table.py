"""Compare a completed oracle run with the same video's audited blind reads."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from last.report import CONDITIONS

# The frozen oracle_reader.py has two byte fingerprints across Git line endings.
FROZEN_ORACLE_HASHES = {
    "807f5a63030a286083504fd26a7f4267abd160014d81e151740a99a24bf1f73e",
    "409645be7cb9209cdc8217242bf1ef2858a40538a83a9755eb21b064fd9e5df0",
}


def load_blind_report(path, manifest_path=None):
    report = json.loads(path.read_bytes())
    if "audited_observations" in report:
        if "sample_ids" not in report:
            if manifest_path is None:
                raise ValueError("Supply --manifest for a full primary pipeline report")
            manifest = manifest_path.read_bytes()
            if (report.get("artifact_verification") is not True or
                    hashlib.sha256(manifest).hexdigest() != report.get("manifest_sha256")):
                raise ValueError("Primary report and supplied manifest differ")
            report["sample_ids"] = [sample["id"] for sample in json.loads(manifest)["samples"]]
        return report
    if (report.get("scope") != "First 100 frozen Hunyuan I2V LAST samples"
            or report.get("plan_sha256") != "510122dc3c5f460f99a71bc4a823dea950e550dbc57b5bd636bc8394d9dcd8fb"
            or report.get("information_bits") != 512):
        raise ValueError("Unrecognized single-method report")
    samples = [f"paper-{i:03d}" for i in range(100)]
    rows = report["observations"]
    expected = {(s, c) for s in samples for c in CONDITIONS}
    if len(rows) != len(expected) or {(r["video_id"], r["condition"]) for r in rows} != expected:
        raise ValueError("Single-method report has missing or duplicate primary observations")
    # These records are the completed map-seed-zero observations of the frozen primary plan.
    return dict(sample_ids=samples, audited_observations=[
        dict(r, family="hunyuan", mode="i2v", method="last", map_seed=0,
             status="completed", total_bits=512) for r in rows])


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
    parser.add_argument("--manifest", type=Path, help="Original sample manifest for a full primary pipeline report")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--oracle", type=Path)
    source.add_argument("--oracle-dir", type=Path, help="Directory containing a receipt for every sample ID in the report")
    parser.add_argument("--video-id")
    parser.add_argument("--count", type=int, help="Compare the first N declared samples with --oracle-dir")
    args = parser.parse_args()
    report = load_blind_report(args.report, args.manifest)
    if args.oracle_dir:
        if args.video_id:
            parser.error("--video-id applies to a single --oracle")
        ids = report["sample_ids"]
        if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r"paper-[0-9]{3}", s) for s in ids):
            raise ValueError("Expected unique primary sample IDs")
        if args.count is not None:
            if not 1 <= args.count <= len(ids):
                parser.error("--count exceeds the available prefix or is below one")
            ids = ids[:args.count]
        results = {c: [] for c in CONDITIONS}
        for s in ids:
            path = args.oracle_dir / ("hunyuan_i2v_oracle_" + s.replace("-", "") + ".json")
            for c, b, o in compare(report, json.loads(path.read_bytes()), s):
                results[c].append((b, o))
        print(f"{len(ids)} paired Hunyuan I2V videos; {512*len(ids)} information bits per condition.")
        print("| Condition | Blind bits | Oracle bits | Both exact | Blind only | Oracle only | Neither exact | Blind bit accuracy | Oracle bit accuracy |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for c, pairs in results.items():
            counts = [sum((b == 512, o == 512) == outcome for b, o in pairs)
                      for outcome in ((True, True), (True, False), (False, True), (False, False))]
            blind_bits = sum(b for b, _ in pairs)
            oracle_bits = sum(o for _, o in pairs)
            total_bits = 512 * len(pairs)
            values = [blind_bits, oracle_bits, *counts,
                      f"{blind_bits / total_bits:.2%}", f"{oracle_bits / total_bits:.2%}"]
            print("| " + " | ".join([c, *map(str, values)]) + " |")
        raise SystemExit(0)
    if args.count is not None:
        parser.error("--count requires --oracle-dir")
    if not args.video_id:
        parser.error("--oracle requires --video-id")
    pairs = compare(report, json.loads(args.oracle.read_bytes()), args.video_id)
    print("| Condition | Blind correct / 512 | Oracle correct / 512 | Difference in correct bits |")
    print("|---|---:|---:|---:|")
    for condition, blind, oracle in pairs:
        print(f"| {condition} | {blind} | {oracle} | {oracle-blind:+d} |")
