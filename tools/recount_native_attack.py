"""Recount one stored native prediction against its original registered attack."""
import argparse
import hashlib
import json
from pathlib import Path

from last.baseline_evaluate import check_extraction
from last.report import CONDITIONS
from last.temporal import attack_map


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recount(run, condition, video_id, reader=None):
    attacks = run / "attacks"
    generation = json.loads((run / "receipt.json").read_bytes())
    source = sha(run / "marked.mp4")
    if generation["status"] not in ("completed", "completed_generation_only") or generation["video_sha256"] != source:
        raise ValueError("Native marked video differs from completed generation")
    attack_file = attacks / (condition + ".json")
    attack = json.loads(attack_file.read_bytes())
    method, family, mode = (generation[k] for k in ("method", "family", "mode"))
    if (attack["status"], attack["method"], attack["family"], attack["condition"], attack["video_id"],
            attack["source_sha256"], attack["map_seed"]) != ("completed", method, family, condition, video_id, source, 0):
        raise ValueError("Native attack differs from the requested primary condition")
    temporal = condition in ("drop", "insert", "clip")
    mapping = attack_map(video_id, condition) if temporal else None
    if attack["attack_map"] != mapping or attack["frames"] != (len(mapping) if temporal else 65):
        raise ValueError("Unexpected edit map or frame count")
    received = sha(run / "marked.mp4" if condition == "clean" else attacks / (condition + ".mp4"))
    reader = reader or attacks / (condition + "-extract")
    receipt = reader / "receipt.json"
    extraction = json.loads(receipt.read_bytes())
    state = sha(run / "maintained_private.pkl")
    check_extraction(extraction, method, mode, received, state, temporal, family)
    if (attack["received_sha256"] != received or attack["state_sha256"] != state or
            attack["extraction_receipt_sha256"] != sha(receipt)):
        raise ValueError("Changed native attack or extraction evidence")
    message = (run / "message.bin").read_bytes()
    prediction = (reader / "decoded.bin").read_bytes()
    pred_digest = hashlib.sha256(prediction).hexdigest()
    message_digest = hashlib.sha256(message).hexdigest()
    for field, actual in (("state_sha256", state), ("message_sha256", message_digest)):
        if field in generation and generation[field] != actual:
            raise ValueError(f"Native generation {field} differs from the scored input")
    if (len(message) != 64 or len(prediction) != 64 or
            attack["message_sha256"] != message_digest or
            attack["decoded_sha256"] != pred_digest or extraction["decoded_sha256"] != pred_digest):
        raise ValueError("Changed native message or prediction")
    correct = 512 - sum((a ^ b).bit_count() for a, b in zip(message, prediction))
    if (attack["correct_bits"], attack["total_bits"], attack["exact_message"]) != (correct, 512, correct == 512):
        raise ValueError("Native bit recount differs from attack receipt")
    return dict(video_id=video_id, method=method, family=family, mode=mode, condition=condition,
                correct_bits=correct, total_bits=512, exact_message=correct == 512,
                source_sha256=source, received_sha256=received, attack_receipt_sha256=sha(attack_file),
                extraction_receipt_sha256=sha(receipt))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--condition", required=True, choices=CONDITIONS)
    p.add_argument("--video-id", required=True)
    p.add_argument("--reader", type=Path, help="Use the archived external native extraction directory")
    a = p.parse_args()
    print(json.dumps(recount(a.run, a.condition, a.video_id, a.reader), indent=2))
