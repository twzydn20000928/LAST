"""Acquire Figure 4 and supplementary Table 5 inputs on Linux."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from last.campaign import source_digest
from last.development import validate_development
from last.development_case import build
from plot_margin_sweep import collect, digest, read


def bind(path, data):
    if path.exists():
        if read(path) != data:
            raise ValueError(f"Existing inputs differ at {path}")
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def import_default(source, target, case, family, model, memory, key, message):
    import numpy as np

    development = read(source / "development.json")
    generation = read(source / "receipt.json")
    quality = read(source / "quality.json")
    if (development["status"] != "completed" or generation["status"] != "completed"
            or read(source / "case.json") != case or generation["method"] != "last"
            or generation["family"] != family or generation["mode"] != "i2v"
            or generation["mu"] != 0.5 or generation["fixed_target"] or generation["uniform_profile"]
            or Path(generation["model_directory"]).resolve() != model.resolve()
            or generation["offload"] != "sequential" or generation["memory_limit_gib"] != memory):
        raise ValueError(f"Default development run does not match requested configuration: {source}")
    plans = [Path(p) for p, h in development["input_sha256"].items() if h == development["plan_sha256"]]
    if (len(plans) != 1 or digest(plans[0]) != development["plan_sha256"]
            or read(plans[0])["source_sha256"] != source_digest()):
        raise ValueError("Use the generation revision recorded in the development plan")
    if key.read_bytes() != (source / "secret.key").read_bytes() or not np.array_equal(
            np.load(source / "message.npy", allow_pickle=False), np.unpackbits(np.frombuffer(message.read_bytes(), dtype=np.uint8))):
        raise ValueError("Private state differs from the requested development case")
    hashes = dict(development["files_sha256"])
    required = {"case.json", "receipt.json", "quality.json", "marked.mp4", "reference.mp4", "codes.pt", "message.npy"}
    if (set(hashes) != required or hashes["case.json"] != generation["case_sha256"]
            or hashes["codes.pt"] != generation["codebook_sha256"] or hashes["marked.mp4"] != generation["marked_sha256"]
            or any(hashes[n+".mp4"] != quality[n+"_sha256"] for n in ("marked", "reference"))):
        raise ValueError("Development file inventory differs from generation or quality receipts")
    hashes["secret.key"] = digest(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as tmp:
        staged = Path(tmp) / "run"
        staged.mkdir()
        for name, expected in hashes.items():
            dest = staged / name
            shutil.copyfile(source / name, dest)
            if digest(dest) != expected:
                raise ValueError(f"Changed development artifact: {name}")
        bind(staged / "reuse.json", dict(development_receipt_sha256=digest(source / "development.json"),
                                         plan_sha256=development["plan_sha256"]))
        staged.rename(target)


def run(args):
    import fcntl

    dev_path = args.configs / "development_manifest.json"
    dev = read(dev_path)
    validate_development(dev, read(args.configs / "primary_manifest.json"))
    dev_hash = digest(dev_path)
    if read(args.state / "state.json")["manifest_sha256"] != dev_hash:
        raise ValueError("Private state belongs to a different manifest")
    protocol = read(args.configs / "paper_v1.json")
    samples = {row["id"]: row for row in dev["samples"]}
    def wait_for_gpu():
        if args.min_free_mib:
            while int(subprocess.check_output(["nvidia-smi", "--id=0", "--query-gpu=memory.free",
                                               "--format=csv,noheader,nounits"], text=True).strip()) < args.min_free_mib:
                time.sleep(30)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "sweep.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        bind(root / "protocol.json", dict(manifest_sha256=dev_hash, model=str(args.model_dir.resolve()),
             family=args.family, paper_sha256=digest(args.configs / "paper_v1.json"),
             memory_gib=args.memory_gib, source_sha256=source_digest()))
        entries = []
        for name in dev["margin_sweep_ids"]:
            sample = samples[name]
            conditioning = args.conditioning / f"prompt-{sample['index']//4:02}"
            case = build(dev, name, "i2v", dev_hash, conditioning)
            key = args.state / "keys" / f"{sample['key_slot']:02}.key"
            message = args.state / "messages" / f"{name}.bin"
            if key.stat().st_size != 32 or message.stat().st_size != 64:
                raise ValueError(f"Invalid development key or message for {name}")
            for mu in protocol["margin_sweep"]["mu"]:
                directory = root / name / f"mu-{mu:g}"
                if (mu == 0.5 and args.reuse_development and not directory.exists()
                        and (args.reuse_development / name / "development.json").is_file()
                        and read(args.reuse_development / name / "development.json")["status"] == "completed"):
                    import_default(args.reuse_development / name, directory, case, args.family,
                                   args.model_dir, args.memory_gib, key, message)
                directory.mkdir(parents=True, exist_ok=True)
                bind(directory / "case.json", case)
                receipt = directory / "receipt.json"
                if receipt.exists() and read(receipt)["status"] != "completed":
                    raise ValueError(f"Inspect unfinished generation at {directory} before retrying")
                common = ["--family", args.family, "--model-dir", args.model_dir.resolve()]
                if not receipt.exists():
                    wait_for_gpu()
                subprocess.run([sys.executable, "-m", "last.smoke", *common, "--mode", "i2v",
                                "--method", "last", "--case", directory / "case.json", "--output", directory,
                                "--key", key, "--message", message, "--offload", "sequential",
                                "--memory-gib", str(args.memory_gib), "--mu", str(mu)], check=True)
                wait_for_gpu()
                subprocess.run([sys.executable, "-m", "last.evaluate", *common, "--run", directory,
                                "--video-id", name], check=True)
                quality = directory / "quality.json"
                if not quality.exists():
                    pending = quality.with_suffix(".tmp")
                    subprocess.run([sys.executable, "-m", "last.quality", "--marked", directory / "marked.mp4",
                                    "--reference", directory / "reference.mp4", "--output", pending], check=True)
                    pending.replace(quality)
                entries.append(dict(video_id=name, run=directory.relative_to(root).as_posix()))
        candidate = root / "candidate-index.json"
        bind(candidate, entries)
        collect(candidate, args.configs)
        candidate.replace(root / "index.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state", "conditioning", "model-dir", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--reuse-development", type=Path, help="Import the three default-margin runs from this development output root")
    parser.add_argument("--family", choices=("hunyuan", "wan22"), default="hunyuan")
    parser.add_argument("--memory-gib", type=float, default=8)
    parser.add_argument("--min-free-mib", type=int, default=0, help="On a shared single GPU, wait for this much free memory before each GPU job")
    os.umask(0o077)
    run(parser.parse_args())
