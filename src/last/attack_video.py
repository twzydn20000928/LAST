"""Apply one primary attack to a standalone 65-frame marked MP4 on CPU."""
import argparse
import os
import tempfile
from pathlib import Path

from .attacks import attacked
from .report import CONDITIONS
from .video import export_mp4, load_mp4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", choices=[c for c in CONDITIONS if c != "clean"], required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--map-seed", type=int, choices=range(5), default=0)
    args = parser.parse_args()
    if os.path.lexists(args.output):
        parser.error(f"Choose a new output file: {args.output}")
    frames = load_mp4(args.video)
    if len(frames) != 65 or any(frame.size != (512, 512) for frame in frames):
        parser.error("The primary attack protocol expects 65 frames at 512 x 512")
    seed = args.map_seed if args.condition in ("drop", "insert", "clip") else 0
    edited, _ = attacked(frames, args.condition, args.video_id, seed=seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        encoded = Path(tmp) / "edited.mp4"
        export_mp4(edited, encoded, crf=28 if args.condition == "compression" else 18)
        os.link(encoded, args.output)
    print(f"{args.condition}: {len(frames)} -> {len(edited)} frames, saved to {args.output}")


if __name__ == "__main__":
    main()
