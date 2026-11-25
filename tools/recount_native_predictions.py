"""Recount scored native readouts using only the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path

CONDITIONS = ("clean", "noise", "compression", "blur", "drop", "insert", "clip")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def recount(run, attacks, condition, clean_extraction=None):
    score = json.loads((attacks / f"{condition}.json").read_bytes())
    folder = clean_extraction if condition == "clean" and clean_extraction else attacks / f"{condition}-extract"
    raw = (folder / "receipt.json").read_bytes()
    extraction = json.loads(raw)
    if (score["condition"], score["status"], extraction["status"]) != (
            condition, "completed", "completed_extraction"):
        raise ValueError(f"Incomplete or mismatched extraction: {condition}")
    truth = (run / "message.bin").read_bytes()
    decoded = (folder / "decoded.bin").read_bytes()
    if len(truth) != 64 or len(decoded) != 64:
        raise ValueError("Expected a 512-bit message and prediction")
    received = run / "marked.mp4" if condition == "clean" else attacks / f"{condition}.mp4"
    received_hash = sha(received.read_bytes())
    if received_hash != score["received_sha256"] or received_hash != extraction["video_sha256"]:
        raise ValueError("Scored and decoded videos differ")
    for field, content in (("extraction_receipt_sha256", raw), ("decoded_sha256", decoded),
                           ("message_sha256", truth)):
        if field in score and sha(content) != score[field]:
            raise ValueError(f"Score digest mismatch: {field}")
    if "decoded_sha256" in extraction and sha(decoded) != extraction["decoded_sha256"]:
        raise ValueError("Prediction differs from extraction receipt")
    correct = 512 - sum(bin(a ^ b).count("1") for a, b in zip(truth, decoded))
    if (score["total_bits"], score["correct_bits"], score["exact_message"]) != (512, correct, correct == 512):
        raise ValueError("Private recount differs from archived score")
    return dict(condition=condition, correct_bits=correct, total_bits=512, exact_message=correct == 512,
                received_sha256=received_hash, extraction_receipt_verified="extraction_receipt_sha256" in score,
                prediction_digest_present="decoded_sha256" in extraction or "decoded_sha256" in score)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--attacks", type=Path)
    parser.add_argument("--clean-extraction", type=Path)
    parser.add_argument("--condition", choices=CONDITIONS)
    args = parser.parse_args()
    rows = [recount(args.run, args.attacks or args.run / "attacks", c, args.clean_extraction)
            for c in ((args.condition,) if args.condition else CONDITIONS)]
    print(json.dumps(rows, indent=2))
