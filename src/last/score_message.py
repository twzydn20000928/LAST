"""Score a blind LAST prediction against a known 512-bit message on CPU."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", type=Path, required=True, help="Original 64-byte message")
    parser.add_argument("--prediction", type=Path, required=True, help="JSON from last.extract")
    args = parser.parse_args()
    try:
        expected = args.message.read_bytes()
        receipt = json.loads(args.prediction.read_text(encoding="utf-8"))
        predicted = bytes.fromhex(receipt["message_hex"])
    except (OSError, KeyError, ValueError, TypeError):
        parser.error("Expected a readable message file and a prediction JSON with a hexadecimal message_hex field")
    if len(expected) != 64 or len(predicted) != 64:
        parser.error("The original and predicted messages must each contain exactly 64 bytes")
    errors = sum(bin(a ^ b).count("1") for a, b in zip(expected, predicted))
    print(json.dumps({"correct_bits": 512 - errors, "total_bits": 512,
                      "bit_accuracy": (512 - errors) / 512, "exact_message": errors == 0}))


if __name__ == "__main__":
    main()
