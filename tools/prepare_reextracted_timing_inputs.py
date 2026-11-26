"""Bind clean and drop timing inputs to an independently verified LAST readout."""
import argparse
import json
from pathlib import Path

from last.reextract_evidence import sha, verified_rows
from last.timing_summary import check_drop_frames


def prepare(run, evidence, source):
    verified = verified_rows(run, evidence, source)
    generation = json.loads((run / "receipt.json").read_bytes())
    case = json.loads((run / "case.json").read_bytes())
    if generation["case_sha256"] != sha(run / "case.json"):
        raise ValueError("Generation case fingerprint mismatch")
    video_id = case["video_id"]
    results = {}
    for condition in ("clean", "drop"):
        prior = run / "attacks" / (condition + ".json")
        attack = json.loads(prior.read_bytes())
        if (attack["video_id"], attack["method"], attack.get("map_seed", 0)) != (video_id, "last", 0):
            raise ValueError("Expected the same LAST sample and primary edit")
        if condition == "drop":
            check_drop_frames(attack, video_id)
        elif attack["frames"] != 65 or attack["attack_map"] is not None:
            raise ValueError("Expected an unedited 65-frame input")
        row = verified[condition]
        results[condition] = dict(
            status=row["status"], method="last", condition=condition, video_id=video_id,
            map_seed=0, attack_map=attack["attack_map"], frames=attack["frames"],
            source_sha256=generation["marked_sha256"], received_sha256=row["received_sha256"],
            prior_receipt_sha256=sha(prior), reextraction_receipt_sha256=row["reextraction_receipt_sha256"],
            scope="Timing input verified from independent re-extraction",
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("run", "evidence", "source", "output"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args()
    records = prepare(args.run, args.evidence, args.source)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, record in records.items():
        (args.output / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
