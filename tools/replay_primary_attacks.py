"""Recreate all six edits from the original marked MP4 without invoking a reader."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from last.evaluate import attacked
from last.report import CONDITIONS
from last.video import export_mp4, load_mp4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(folder):
    case = json.loads((folder/"case.json").read_bytes())
    source = folder/"marked.mp4"
    source_hash = digest(source)
    frames = load_mp4(source)
    if len(frames) != 65 or source_hash != json.loads((folder/"receipt.json").read_bytes())["marked_sha256"]:
        raise ValueError("Expected the completed original 65-frame video")
    result = {}
    with TemporaryDirectory() as tmp:
        for condition in CONDITIONS:
            receipt = json.loads((folder/"attacks"/(condition+".json")).read_bytes())
            if (receipt["status"] != "completed" or receipt["source_sha256"] != source_hash
                    or receipt["video_id"] != case["video_id"] or receipt["condition"] != condition
                    or receipt.get("map_seed", 0) != 0):
                raise ValueError(f"Different acquisition case: {condition}")
            recorded = source if condition == "clean" else folder/"attacks"/(condition+".mp4")
            if digest(recorded) != receipt["received_sha256"]:
                raise ValueError(f"Recorded MP4 has changed: {condition}")
            edited, mapping = attacked(frames, condition, case["video_id"])
            reconstructed = source
            if condition != "clean":
                reconstructed = Path(tmp)/(condition+".mp4")
                export_mp4(edited, reconstructed, crf=28 if condition == "compression" else 18)
            replay_hash = digest(reconstructed)
            count = len(load_mp4(reconstructed))
            result[condition] = dict(recorded_sha256=receipt["received_sha256"], replay_sha256=replay_hash,
                                     same_bytes=replay_hash == receipt["received_sha256"],
                                     same_map=mapping == receipt["attack_map"], frames=count,
                                     same_length=count == receipt["frames"])
    return dict(video_id=case["video_id"], source_sha256=source_hash, conditions=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.run)
    print(json.dumps(result, indent=2))
    if not all(r["same_bytes"] and r["same_map"] and r["same_length"] for r in result["conditions"].values()):
        raise SystemExit(1)
