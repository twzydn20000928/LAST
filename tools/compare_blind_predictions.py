"""Compare two private blind-extraction outputs against the same received MP4."""
import argparse
import hashlib
import json
from pathlib import Path


def payload(report, video_digest):
    if report["information_bits"] != 512 or report["video_sha256"] != video_digest:
        raise ValueError("Expected a 512-bit extraction from the supplied MP4")
    raw = bytes.fromhex(report["message_hex"])
    if len(raw) != 64:
        raise ValueError("Decoded message must contain exactly 64 bytes")
    return raw


def compare(video, first, second=None, controlled_read=None):
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    primary = json.loads(first.read_bytes())
    left = payload(primary, digest)
    if (second is None) == (controlled_read is None):
        raise ValueError("Supply one second prediction or one controlled read")
    if controlled_read is None:
        other = json.loads(second.read_bytes())
        right = payload(other, digest)
        for key in ("family", "frames"):
            if primary[key] != other[key]:
                raise ValueError(f"Reader metadata differs: {key}")
    else:
        record = json.loads((controlled_read / "receipt.json").read_bytes())
        data = (controlled_read / "decoded-private.json").read_bytes()
        if (record["status"] != "completed" or record["blind"] is not True
                or record["reader"] not in ("received", "ccta", "calibrated_energy")
                or record["input_sha256"].get(str(video.resolve())) != digest
                or record["decoded_sha256"] != hashlib.sha256(data).hexdigest()):
            raise ValueError("Controlled read must verify the same MP4 and private prediction")
        bits = json.loads(data)["information_bits"]
        if len(bits) != 512 or any(type(b) is not int or b not in (0, 1) for b in bits):
            raise ValueError("Expected 512 binary information bits")
        right = int("".join(str(b) for b in bits), 2).to_bytes(64, "big")
    differences = sum((a ^ b).bit_count() for a, b in zip(left, right))
    return dict(video_sha256=digest, family=primary["family"], frames=primary["frames"],
                equal_prediction_bits=512-differences, total_bits=512, identical=differences == 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "first"):
        parser.add_argument("--" + name, required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--second", type=Path)
    source.add_argument("--controlled-read", type=Path, help="Directory of a completed controlled blind read")
    args = parser.parse_args()
    print(json.dumps(compare(args.video, args.first, args.second, args.controlled_read), indent=2))
