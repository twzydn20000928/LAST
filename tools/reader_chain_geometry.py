"""Replay temporal reader-chain geometry after blind extraction."""
import argparse
import hashlib
import json
from pathlib import Path

from deletion_chain_audit import window_support
from last.temporal import attack_map

TEMPORAL = ("drop", "insert", "clip")
WINDOW_LABELS = {
    "contains_inserted_frame": "inserted",
    "contains_initial_frame": "prefix",
    "spans_source_groups": "mixed",
    "intact_correct_identity": "intact_correct",
    "intact_wrong_identity": "intact_wrong",
}


def collect(report, index_path):
    folders = json.loads(index_path.read_bytes())
    records = {}
    for row in report["observations"]:
        key = row["video_id"], row["condition"], row["variant"]
        if key in records:
            raise ValueError(f"Duplicate reader observation: {key}")
        records[key] = row
    result = []
    for (video, condition, variant), full in records.items():
        if variant != "full" or condition not in TEMPORAL:
            continue
        folder = index_path.parent / folders[video]
        for reader in ("full", "without_ccta"):
            observed = records[video, condition, reader]
            raw = (folder / f"{condition}-{reader}.json").read_bytes()
            receipt = json.loads(raw)
            identity = tuple(receipt[k] for k in ("video_id", "condition", "variant", "status"))
            if (identity != (video, condition, reader, "completed")
                    or hashlib.sha256(raw).hexdigest() != observed["receipt_sha256"]
                    or receipt["video_sha256"] != observed["received_sha256"]
                    or receipt["video_sha256"] != full["received_sha256"]
                    or receipt["correct_bits"] != observed["correct_bits"]):
                raise ValueError(f"Reader source mismatch for {video}/{condition}/{reader}")
            if reader == "full":
                blind = receipt
        chains = [{k: chain[k] for k in ("start", "first_group", "length")} for chain in blind["chains"]]
        support, types = window_support(video, attack_map(video, condition), chains, blind["groups"])
        result.append(dict(video_id=video, condition=condition, route=blind["route"], chains=chains,
                           support=[support[k] for k in range(5)],
                           window_types={WINDOW_LABELS[k]: v for k, v in types.items()},
                           full_bits=full["correct_bits"], received_order_bits=records[video, condition, "without_ccta"]["correct_bits"],
                           full_receipt_sha256=full["receipt_sha256"], received_sha256=full["received_sha256"]))
    videos = {key[0] for key in records}
    if not videos or len(result) != len(videos) * len(TEMPORAL):
        raise ValueError("All three temporal attacks are required per video")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True, help="JSON mapping video IDs to reader-receipt directories")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = collect(json.loads(args.report.read_bytes()), args.index)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(rows, stream, indent=2)

