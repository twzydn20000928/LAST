"""Compare two private blind-extraction outputs against the same received MP4."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(video, first, second):
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    reports = [json.loads(path.read_bytes()) for path in (first, second)]
    payloads = []
    for r in reports:
        if r["information_bits"] != 512 or r["video_sha256"] != digest:
            raise ValueError("Expected a 512-bit extraction from the supplied MP4")
        raw = bytes.fromhex(r["message_hex"])
        if len(raw) != 64:
            raise ValueError("Decoded message must contain exactly 64 bytes")
        payloads.append(raw)
    for key in ("family", "frames"):
        if reports[0][key] != reports[1][key]:
            raise ValueError(f"Reader metadata differs: {key}")
    differences = sum((a ^ b).bit_count() for a, b in zip(*payloads))
    return dict(video_sha256=digest, family=reports[0]["family"], frames=reports[0]["frames"],
                equal_prediction_bits=512-differences, total_bits=512, identical=differences == 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "first", "second"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.video, args.first, args.second), indent=2))
