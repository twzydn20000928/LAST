"""Recreate all six edits from the original marked MP4 without invoking a reader."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from last.evaluate import attacked
from last.report import CONDITIONS
from last.video import export_mp4, load_mp4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(folder, *, legacy=False):
    case = json.loads((folder/"case.json").read_bytes())
    source = folder/"marked.mp4"
    source_hash = digest(source)
    frames = load_mp4(source)
    generation = json.loads((folder/"receipt.json").read_bytes())
    if len(frames) != 65 or generation.get("status") != "completed" or source_hash != generation["marked_sha256"]:
        raise ValueError("Expected the completed original 65-frame video")
    result = {}
    with TemporaryDirectory() as tmp:
        for condition in CONDITIONS:
            original = (folder/"attacks"/(condition+".json")).read_bytes()
            receipt = json.loads(original)
            if (receipt["status"] != "completed" or receipt["source_sha256"] != source_hash
                    or receipt["video_id"] != case["video_id"] or receipt["condition"] != condition
                    or receipt.get("map_seed", 0) != 0):
                raise ValueError(f"Different acquisition case: {condition}")
            recorded = source if condition == "clean" else folder/"attacks"/(condition+".mp4")
            recorded_hash = digest(recorded)
            if "received_sha256" not in receipt and not legacy:
                raise ValueError(f"Missing original received MP4 digest: {condition}")
            if receipt.get("received_sha256", recorded_hash) != recorded_hash:
                raise ValueError(f"Recorded MP4 has changed: {condition}")
            edited, mapping = attacked(frames, condition, case["video_id"])
            reconstructed = source
            if condition != "clean":
                reconstructed = Path(tmp)/(condition+".mp4")
                export_mp4(edited, reconstructed, crf=28 if condition == "compression" else 18)
            replay_hash = digest(reconstructed)
            count = len(load_mp4(reconstructed))
            result[condition] = dict(recorded_sha256=recorded_hash, replay_sha256=replay_hash,
                                     same_bytes=replay_hash == recorded_hash,
                                     same_map=mapping == receipt["attack_map"], frames=count,
                                     same_length=count == receipt["frames"])
            if legacy:
                result[condition]["prior_receipt_sha256"] = hashlib.sha256(original).hexdigest()
    return dict(video_id=case["video_id"], source_sha256=source_hash, conditions=result)


def write_view(folder, output, result):
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        view = Path(temporary) / "view"
        (view / "attacks").mkdir(parents=True)
        view.chmod(0o700)
        for name in ("case.json", "receipt.json", "marked.mp4", "message.npy", "codes.pt"):
            (view / name).symlink_to((folder / name).resolve(strict=True))
        for condition, checks in result["conditions"].items():
            original = (folder / "attacks" / (condition + ".json")).read_bytes()
            if hashlib.sha256(original).hexdigest() != checks["prior_receipt_sha256"]:
                raise ValueError(f"Attack receipt changed during replay: {condition}")
            row = json.loads(original)
            row.update(received_sha256=checks["replay_sha256"], prior_receipt_sha256=checks["prior_receipt_sha256"])
            if condition != "clean":
                video = (folder / "attacks" / (condition + ".mp4")).resolve(strict=True)
                (view / "attacks" / video.name).symlink_to(video)
            (view / "attacks" / (condition + ".json")).write_text(json.dumps(row, indent=2))
        view.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--ablation-view", type=Path,
                        help="Prepare a new private reader-ablation directory after byte-exact historical replay")
    args = parser.parse_args()
    if args.ablation_view:
        os.umask(0o077)
    result = replay(args.run, legacy=args.ablation_view is not None)
    print(json.dumps(result, indent=2))
    if not all(r["same_bytes"] and r["same_map"] and r["same_length"] for r in result["conditions"].values()):
        raise SystemExit(1)
    if args.ablation_view:
        write_view(args.run, args.ablation_view, result)
