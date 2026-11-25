"""Replay CPU candidate generation on the archived random-deletion MP4s."""
import argparse
import hashlib
import json
from pathlib import Path

from last.temporal import attack_map, segments, windows


def audit(root, report_bytes):
    from last.video import load_mp4
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


def recovery_by_stage(candidates, report_bytes):
    """Join archived candidate counts to post-decoding outcomes for the same videos."""
    # Git's Windows archive and the published blob can differ only in line endings.
    lf = report_bytes.replace(b"\r\n", b"\n")
    digests = {hashlib.sha256(data).hexdigest() for data in (lf, lf.replace(b"\n", b"\r\n"), report_bytes)}
    if candidates["report_sha256"] not in digests:
        raise ValueError("Candidate replay used a different message report")
    report = json.loads(report_bytes)
    messages = {row["video_id"]: row for row in report["observations"]["drop"]}
    ids = report["sample_ids"]
    if len(messages) != len(report["observations"]["drop"]) or set(messages) != set(ids) or len(ids) != len(messages):
        raise ValueError("Incomplete or duplicated deletion outcomes")
    cells = {}
    for row in candidates["observations"]:
        vid = row["video_id"]
        if vid not in messages:
            raise ValueError(f"Unexpected or duplicated candidate replay: {vid}")
        message = messages.pop(vid)
        hits, proposed, survived = (row[k] for k in ("selected_correct", "proposed", "surviving"))
        bits = message["correct_bits"]
        if (not 0 <= hits <= proposed <= survived <= 16 or type(bits) is not int or not 0 <= bits <= 512):
            raise ValueError(f"Inconsistent candidate or recovery counts: {vid}")
        if hits:
            stage = "selected_correct_intact"
        elif proposed:
            stage = "intact_candidate_missed"
        elif survived:
            stage = "intact_group_never_proposed"
        else:
            stage = "no_intact_group_survived"
        cell = cells.setdefault(stage, dict(videos=0, correct_bits=0, total_bits=0, exact_messages=0))
        cell["videos"] += 1
        cell["correct_bits"] += bits
        cell["total_bits"] += 512
        cell["exact_messages"] += int(bits == 512)
    if messages:
        raise ValueError("Missing candidate replays")
    return cells


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--root", type=Path)
    mode.add_argument("--saved-candidates", type=Path, help="Join the public candidate replay to decoded outcomes on CPU")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report_bytes = args.report.read_bytes()
    result = (recovery_by_stage(json.loads(args.saved_candidates.read_bytes()), report_bytes)
              if args.saved_candidates else audit(args.root, report_bytes))
    print(json.dumps(result, indent=2))
