"""Collect LAST development features and wrong-key responses on a Linux experiment host."""
import argparse
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

from last.development import validate_development
from last.feature_cache import load, sha
from last.null_cache import acquire, read_keys
from last.null_energy import validate_keys


def read(path):
    return json.loads(path.read_bytes())


def collect(args):
    development, primary = read(args.development), read(args.primary)
    validate_development(development, primary)
    vae_files = {f.name: sha(f) for f in (args.model_dir / "vae").iterdir()
                 if f.is_file() and f.suffix in (".json", ".safetensors", ".bin")}
    if not vae_files:
        raise ValueError("No frozen VAE files found")
    bank, real = read_keys(args.wrong_keys), read_keys(args.real_keys)
    validate_keys(bank, real)
    if len(real) != 16:
        raise ValueError("Supply all eight development and eight primary keys")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "collection.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        entries = []
        for sample in development["samples"]:
            name = sample["id"]
            run = args.runs / name
            dest = args.output / name
            video = run / "marked.mp4"
            generation = read(run / "receipt.json")
            case = read(run / "case.json")
            if (generation["status"] != "completed" or generation["method"] != "last"
                    or generation["mode"] != "i2v" or generation["mu"] != 0.5
                    or generation["fixed_target"] or generation["uniform_profile"]
                    or generation["marked_sha256"] != sha(video)
                    or generation["case_sha256"] != sha(run / "case.json")
                    or case["development_manifest_sha256"] != sha(args.development)
                    or (case["video_id"], case["seed"], case["prompt"], case["key_slot"])
                    != (name, sample["seed"], sample["prompt"], sample["key_slot"])):
                raise ValueError(f"Generation differs from development protocol: {name}")
            dest.mkdir(exist_ok=True)
            features, responses = dest / "features", dest / "responses"
            if not features.exists():
                subprocess.run([sys.executable, "-m", "last.feature_cache", "--video", video,
                                "--family", generation["family"], "--model-dir", args.model_dir,
                                "--output", features], check=True)
            _, _, record = load(features, video)
            if (record["family"] != generation["family"] or record["reader"] != "ccta"
                    or not record["scan"] or record["vae_files_sha256"] != vae_files):
                raise ValueError(f"Unexpected candidate cache: {name}")
            if not responses.exists():
                acquire(features, video, args.wrong_keys, args.real_keys, responses)
            response = read(responses / "receipt.json")
            inputs = (video, features / "receipt.json", features / "nodes.json", features / "features.npy",
                      args.wrong_keys, args.real_keys)
            if (response["status"] != "completed" or response["energies_sha256"] != sha(responses / "energies.npy")
                    or response["input_sha256"] != {str(path.resolve()): sha(path) for path in inputs}):
                raise ValueError(f"Response inputs or output differ: {name}")
            entries.append(dict(video_id=name, run=str(run.resolve()), features=str(features.resolve()),
                                responses=str(responses.resolve())))
        temp = args.output / "index.tmp"
        temp.write_text(json.dumps(entries, indent=2))
        temp.replace(args.output / "index.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("development", "primary", "runs", "model-dir", "wrong-keys", "real-keys", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    os.umask(0o077)
    collect(parser.parse_args())
