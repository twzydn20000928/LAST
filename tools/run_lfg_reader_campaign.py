"""Run supplementary Table 12 on completed primary Hunyuan I2V LFG videos."""
import argparse
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

from last.data import validate
from lfg_reader_pairs import audit


def run(args):
    manifest = json.loads(args.manifest.read_bytes())
    validate(manifest)
    samples = manifest["samples"]
    if not 0 <= args.first < args.stop <= len(samples) or args.poll_seconds <= 0:
        raise ValueError("Invalid sample range or poll interval")
    args.outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
    for sample in samples[args.first:args.stop]:
        video = sample["id"]
        primary = args.root / "hunyuan/i2v/lfg" / video
        with (args.outputs / (video + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            receipt = primary / "campaign.json"
            while True:
                status = json.loads(receipt.read_bytes())["status"] if receipt.exists() else "missing"
                if status == "completed":
                    break
                if status == "failed" or not args.follow:
                    raise RuntimeError(f"{video}: primary generation/evaluation is {status}")
                print(f"{video}: waiting for primary ({status})", flush=True)
                time.sleep(args.poll_seconds)
            out = args.outputs / video
            if not out.exists():
                subprocess.run([sys.executable, "-m", "last.lfg_native_reader", "--family", "hunyuan",
                                "--model-dir", str(args.model_dir), "--run", str(primary),
                                "--output", str(out)], check=True)
            # Verify existing and newly finished outputs by the same seven-condition recount.
            audit(None, args.root, args.outputs, [sample])
            print(f"{video}: seven paired observations verified", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "outputs", "model-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--first", type=int, default=0)
    parser.add_argument("--stop", type=int, default=400, help="Exclusive upper sample index")
    parser.add_argument("--follow", action="store_true", help="Wait for the next primary case to finish")
    parser.add_argument("--poll-seconds", type=int, default=120)
    run(parser.parse_args())
