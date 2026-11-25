"""Replay CPU candidate generation on the archived random-deletion MP4s."""
import argparse
import hashlib
import json
from pathlib import Path

from last.temporal import attack_map, segments, windows
from last.video import load_mp4


def audit(root, report_bytes):
    report = json.loads(report_bytes)
    rows = report["observations"]["drop"]
    ids = [r["video_id"] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(report["sample_ids"]):
        raise ValueError("Deletion records differ from the declared sample set")
    observations = []
    for row in rows:
        video = row["video_id"]
        folder = root / "hunyuan/i2v/last" / video / "attacks"
        receipt = (folder / "drop.json").read_bytes()
        mp4 = folder / "drop.mp4"
        saved = json.loads(receipt)
        mapping = attack_map(video, "drop")
        if (hashlib.sha256(receipt).hexdigest() != row["receipt_sha256"]
                or hashlib.sha256(mp4.read_bytes()).hexdigest() != row["received_sha256"]
                or saved["received_sha256"] != row["received_sha256"]
                or saved["attack_map"] != mapping or saved["route"] != "ccta"):
            raise ValueError(f"Unexpected archived input or extraction route: {video}")
        frames = load_mp4(mp4)
        if len(frames) != len(mapping):
            raise ValueError(f"Decoded length differs from attack map: {video}")
        starts = {w["start"] for w in windows(segments(frames)) if not w["padded"]}
        intact = {i: (mapping[i] - 1) // 4 for i in range(len(mapping) - 3)
                  if mapping[i] % 4 == 1 and mapping[i:i+4] == list(range(mapping[i], mapping[i]+4))}
        hits = set()
        for chain in saved["chains"]:
            for offset in range(chain["length"]):
                start = chain["start"] + 4 * offset
                if start not in starts:
                    raise ValueError(f"Saved chain window missing from replay: {video}")
                if intact.get(start) == chain["first_group"] + offset:
                    hits.add(start)
        observations.append(dict(video_id=video, surviving=len(intact),
                                 proposed=len(starts.intersection(intact)), selected_correct=len(hits)))
    return dict(report_sha256=hashlib.sha256(report_bytes).hexdigest(), observations=observations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.report.read_bytes()), indent=2))
