"""Construct matched-duration MP4 inputs for a supplementary timing diagnostic."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from last.video import export_mp4, load_mp4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Completed 65-frame LAST generation directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a fresh output directory")
    receipt_path = args.run / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    source = args.run / "marked.mp4"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if (receipt["status"] != "completed" or receipt.get("method") != "last"
            or digest != receipt["marked_sha256"]):
        parser.error("Expected a verified completed LAST source")
    frames = load_mp4(source)
    if len(frames) != 65:
        parser.error("Expected 65 decoded source frames")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output.parent) as temporary:
        stage = Path(temporary) / "clips"
        stage.mkdir()
        rows = []
        for length in (65, 129, 257):
            indices = [64 - abs(i % 128 - 64) for i in range(length)]
            target = stage / f"{length}.mp4"
            export_mp4([frames[i] for i in indices], target, crf=18, fps=8)
            if len(load_mp4(target)) != length:
                raise ValueError(f"Frame count mismatch for {target.name}")
            rows.append(dict(file=target.name, frames=length, source_indices=indices,
                             sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
        record = dict(scope="Timing-only forward/reverse reconstruction from one 65-frame source",
                      source_sha256=digest, generation_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                      crf=18, fps=8, clips=rows)
        (stage / "inputs.json").write_text(json.dumps(record, indent=2) + "\n")
        stage.rename(args.output)


if __name__ == "__main__":
    main()
