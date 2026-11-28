"""Prepare reproducible inputs for the public sailboat example on CPU."""
import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="A new directory")
    args = parser.parse_args()
    label = "LAST public reader demonstration v1"
    with tempfile.TemporaryDirectory() as temporary:
        demo_key = Path(temporary) / "demo.key"
        demo_key.write_bytes(hashlib.sha256(label.encode("ascii")).digest())
        subprocess.run(
            [
                sys.executable, "-m", "last.cli", "prepare-video",
                "--output", str(args.output),
                "--key-file", str(demo_key),
                "--text", label,
                "--prompt", "A small red sailboat moves slowly across a calm blue lake under a clear sky.",
                "--seed", "42",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
