"""Recover public per-video BCH counts from the eight archived re-extractions."""
import argparse
import json
from pathlib import Path

from last.report import CONDITIONS
from primary_deletion_errors import digest


def export(root, archive, blind):
    hashes = archive["replay_receipt_sha256"]
    inputs = {(r["video_id"], r["condition"]): r for r in blind["observations"]}
    observations = {c: [] for c in CONDITIONS}
    for video, fingerprint in hashes.items():
        path = root / video / "receipt.json"
        if digest(path) != fingerprint:
            raise ValueError(f"Re-extraction receipt changed: {video}")
        receipt = json.loads(path.read_bytes())
        rows = receipt["rows"]
        if receipt["status"] != "completed" or sorted(r["condition"] for r in rows) != sorted(CONDITIONS):
            raise ValueError(f"Incomplete re-extraction: {video}")
        for r in rows:
            condition = r["condition"]
            original = inputs[video, condition]
            if (r["status"] != "completed" or r["received_sha256"] != original["video_sha256"]
                    or r["prior_receipt_sha256"] != original["receipt_sha256"]
                    or r["correct_bits"] != original["correct_bits"] or r["total_bits"] != 512):
                raise ValueError(f"Blind observations differ: {video}/{condition}")
            observations[condition].append(dict(video_id=video, received_sha256=r["received_sha256"],
                                                correct_bits=r["correct_bits"], bch_success=r["bch_success"],
                                                raw_information_correct=r["raw_information_correct"]))
    for condition, rows in observations.items():
        totals = archive["conditions"][condition]
        if (sum(512-r["raw_information_correct"] for r in rows) != totals["pre_bch_wrong_bits"]
                or sum(512-r["correct_bits"] for r in rows) != totals["post_bch_wrong_bits"]
                or sum(r["correct_bits"] == 512 for r in rows) != totals["post_bch_exact_messages"]):
            raise ValueError(f"Archived BCH counts differ: {condition}")
    return dict(manifest_sha256=blind["manifest_sha256"], replay_receipt_sha256=hashes,
                sample_ids=list(hashes), observations=observations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    results = Path(__file__).resolve().parents[1] / "results"
    archive = json.loads((results / "primary_pre_post_bch_eight_replays.json").read_bytes())
    blind = json.loads((results / "hunyuan_i2v_last_first100_robustness.json").read_bytes())
    data = export(args.root, archive, blind)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")
