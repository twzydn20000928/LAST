"""Score a blind LAST prediction against a known 512-bit message on CPU."""
import argparse
import json
from pathlib import Path


def score_prediction(expected, receipt, show_errors, padded_text=False):
    predicted = bytes.fromhex(receipt["message_hex"])
    if len(predicted) != 64:
        raise ValueError("Expected a 64-byte prediction")
    errors = sum(bin(a ^ b).count("1") for a, b in zip(expected, predicted))
    score = {"correct_bits": 512 - errors, "total_bits": 512,
             "bit_accuracy": (512 - errors) / 512, "exact_message": errors == 0}
    if padded_text:
        body = expected.rstrip(b"\x00")
        body.decode("utf-8")
        body_bits = 8 * len(body)
        body_errors = sum(bin(a ^ b).count("1") for a, b in zip(body, predicted))
        padding_bits = 512 - body_bits
        try:
            predicted.rstrip(b"\x00").decode("utf-8")
            valid_utf8 = True
        except UnicodeDecodeError:
            valid_utf8 = False
        score["padded_text"] = {"body_bits": body_bits, "correct_body_bits": body_bits - body_errors,
                                "padding_bits": padding_bits, "correct_padding_bits": padding_bits - (errors - body_errors),
                                "valid_utf8": valid_utf8}
    if show_errors:
        score["wrong_bit_positions"] = [
            8 * byte_index + bit_index
            for byte_index, (original, recovered) in enumerate(zip(expected, predicted))
            for bit_index in range(8)
            if (original ^ recovered) & (0x80 >> bit_index)
        ]
    return score


def score_summary(path, expected, show_errors, padded_text=False):
    summary = json.loads(path.read_bytes())
    results = {}
    for condition in summary["requested"]:
        row = summary["results"].get(condition, {"status": "pending"})
        if row["status"] != "completed":
            results[condition] = {k: row[k] for k in ("status", "stage", "exit_code") if k in row}
            continue
        name = row.get("prediction", f"{condition}-prediction.json")
        if Path(name).name != name or name != f"{condition}-prediction.json":
            raise ValueError(f"Unexpected prediction filename for {condition}")
        prediction = json.loads((path.parent / name).read_bytes())
        if prediction["video_sha256"] != row["received_sha256"] or prediction["frames"] != row["frames"]:
            raise ValueError(f"Prediction does not match the recorded video for {condition}")
        results[condition] = dict(status="completed", **score_prediction(expected, prediction, show_errors, padded_text))
    return {"video_id": summary["video_id"], "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", type=Path, required=True, help="Original 64-byte message")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--prediction", type=Path, help="JSON from last.extract")
    inputs.add_argument("--summary", type=Path, help="summary.json from last.check_video")
    parser.add_argument("--show-errors", action="store_true",
                        help="Include zero-based wrong bit positions, most significant bit first in each byte")
    parser.add_argument("--padded-text", action="store_true",
                        help="For zero-padded UTF-8 messages, score body and padding separately and check recovered UTF-8")
    args = parser.parse_args()
    try:
        expected = args.message.read_bytes()
        if len(expected) != 64:
            raise ValueError("Expected a 64-byte original message")
        if args.summary:
            result = score_summary(args.summary, expected, args.show_errors, args.padded_text)
        else:
            result = score_prediction(expected, json.loads(args.prediction.read_bytes()), args.show_errors, args.padded_text)
    except (OSError, KeyError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
