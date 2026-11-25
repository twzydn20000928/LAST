"""Combine original measurements and independent re-extractions on disjoint primary IDs."""
import argparse
import json
import re
from pathlib import Path

from paired_lfg_table import CONDITIONS, RESULTS, count_bits


def read(name):
    return json.loads((RESULTS / name).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--additional-original", type=Path, nargs="+", default=[],
                        help="Additional disjoint original message reports extending the primary prefix")
    parser.add_argument("--verify-original-slice", type=Path,
                        help="Cross-check an audited Hunyuan I2V LAST report against original observations")
    args = parser.parse_args()
    primary = read("hunyuan_i2v_primary_message_170.json")
    replay = read("primary_pre_post_bch_eight_replays.json")
    first100 = read("hunyuan_i2v_last_first100_robustness.json")
    deletion = read("hunyuan_i2v_primary_deletion_errors.json")
    primary_ids = set(primary["sample_ids"])
    replay_ids = set(replay["replay_receipt_sha256"])
    for path in args.additional_original:
        extra = json.loads(path.read_bytes())
        ids = set(extra["sample_ids"])
        if (not ids or len(ids) != len(extra["sample_ids"]) or ids & (primary_ids | replay_ids) or
                extra["manifest_sha256"] != primary["manifest_sha256"]):
            raise ValueError("Additional original cohort overlaps or belongs to another manifest")
        for c in CONDITIONS:
            group = extra["observations"][c]
            if len(group) != len(ids) or {r["video_id"] for r in group} != ids:
                raise ValueError(f"Incomplete added cohort: {c}")
            primary["observations"][c].extend(group)
        primary_ids.update(ids)
    if not (primary["manifest_sha256"] == first100["manifest_sha256"] == deletion["manifest_sha256"]):
        raise ValueError("Reports use different manifests")
    if replay_ids != set(deletion["excluded_missing_received_hash"]) or replay_ids & primary_ids:
        raise ValueError("Expected separate original and re-extraction cohorts")
    n = len(primary_ids) + len(replay_ids)
    if primary_ids | replay_ids != {f"paper-{i:03d}" for i in range(n)}:
        raise ValueError("Combined IDs do not cover the primary prefix")
    if args.verify_original_slice:
        audited = json.loads(args.verify_original_slice.read_bytes())
        ids = set(audited["sample_ids"])
        if (audited["manifest_sha256"] != primary["manifest_sha256"] or not audited["artifact_verification"]
                or not ids or len(ids) != len(audited["sample_ids"]) or not ids <= primary_ids):
            raise ValueError("Audit slice must contain distinct original samples on the same manifest")
        expected = {(r["video_id"], c): (r["receipt_sha256"], r["received_sha256"], r["correct_bits"])
                    for c in CONDITIONS for r in primary["observations"][c] if r["video_id"] in ids}
        observed = {}
        for row in audited["audited_observations"]:
            if (row["family"], row["mode"], row["method"], row["map_seed"], row["status"]) != (
                    "hunyuan", "i2v", "last", 0, "completed"):
                raise ValueError("Unexpected pipeline or status in original cross-check")
            key = (row["video_id"], row["condition"])
            if key in observed:
                raise ValueError(f"Duplicate audit observation: {key}")
            observed[key] = (row["receipt_sha256"], row["video_sha256"], row["correct_bits"])
        if len(expected) != len(ids) * len(CONDITIONS) or expected != observed:
            raise ValueError("Original and slice receipt, received video or information-bit count differs")
    print("| Condition | Original correct bits | Replay correct bits | Combined accuracy | Exact messages |")
    print("|---|---:|---:|---:|---:|---:|")
    for c in CONDITIONS:
        original = primary["observations"][c]
        subset = [r for r in first100["observations"] if r["condition"] == c and r["video_id"] in replay_ids]
        for rows, ids in ((original, primary_ids), (subset, replay_ids)):
            if len(rows) != len(ids) or {r["video_id"] for r in rows} != ids:
                raise ValueError(f"Incomplete or duplicate observations: {c}")
        overlaps = [r for r in first100["observations"] if r["condition"] == c and r["video_id"] in primary_ids]
        original_by_id = {r["video_id"]: r for r in original}
        if len(overlaps) != 92 or len({r["video_id"] for r in overlaps}) != 92:
            raise ValueError("Expected 92 overlapping original observations per condition")
        for row in overlaps:
            other = original_by_id[row["video_id"]]
            if (row["receipt_sha256"], row["video_sha256"], row["correct_bits"]) != (
                    other["receipt_sha256"], other["received_sha256"], other["correct_bits"]):
                raise ValueError(f"Original evidence disagrees for {row['video_id']}/{c}")
        for row in subset:
            if not all(re.fullmatch("[0-9a-f]{64}", row[k]) for k in
                       ("receipt_sha256", "reextraction_receipt_sha256", "video_sha256")):
                raise ValueError(f"Missing re-extraction provenance for {row['video_id']}/{c}")
        old, new = [[count_bits(dict(total_bits=512, **r)) for r in rows] for rows in (original, subset)]
        check = replay["conditions"][c]
        if (check["total_information_bits"] != 512*len(new) or check["post_bch_wrong_bits"] != 512*len(new)-sum(new)
                or check["post_bch_exact_messages"] != new.count(512)):
            raise ValueError(f"Independent recount disagrees: {c}")
        print(f"| {c} | {sum(old)}/{512*len(old)} | {sum(new)}/{512*len(new)} | "
              f"{(sum(old)+sum(new))/(512*n):.2%} | {old.count(512)+new.count(512)}/{n} |")


if __name__ == "__main__":
    main()
