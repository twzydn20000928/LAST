"""Generate and evaluate the LFG-C counterpart of a completed primary LAST case."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import fcntl

import numpy as np
from controlled_batch_commands import check_writer


def match_codebook(last, counterpart):
    """Reuse the original tensor for new runs; verify already-generated pairs."""
    import torch

    source = last / "codes.pt"
    target = counterpart / "codes.pt"
    recorded = json.loads((last / "receipt.json").read_bytes())["codebook_sha256"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != recorded:
        raise ValueError("LAST codebook differs from its generation receipt")
    receipt = counterpart / "receipt.json"
    if not target.exists():
        if receipt.exists():
            raise ValueError("Existing LFG-C generation has no retained codebook")
        temp = counterpart / "codes.tmp"
        shutil.copyfile(source, temp)
        temp.replace(target)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if receipt.exists() and json.loads(receipt.read_bytes()).get("codebook_sha256") != actual:
        raise ValueError("LFG-C codebook differs from its generation receipt")
    if actual != recorded:
        # Equal tensors can have different torch.save archive metadata.
        a, b = (torch.load(p, weights_only=True, map_location="cpu") for p in (source, target))
        if a.dtype != b.dtype or not torch.equal(a, b):
            raise ValueError("LAST and LFG-C use different carrier tensors")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("plan", "manifest", "runs", "model", "state"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--video-id", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    manifest = args.manifest.read_bytes()
    plan = json.loads(args.plan.read_bytes())
    if hashlib.sha256(manifest).hexdigest() != plan["manifest_sha256"]:
        raise ValueError("Unexpected sample manifest")
    sample, = [s for s in json.loads(manifest)["samples"] if s["id"] == args.video_id]
    items = [item for item in plan["runs"] if item["video_id"] == args.video_id]
    writers = {item["method"]: item for item in items}
    if len(items) != 2 or set(writers) != {"last", "lfg-c"}:
        raise ValueError("Expected one planned case for each writer")
    family = writers["last"]["family"]
    if family not in ("wan22", "hunyuan"):
        raise ValueError("Unsupported generation model")
    for method, item in writers.items():
        if (item["run"] != f"{family}/i2v/{method}/{sample['id']}" or
                any(item[k] != sample[k] for k in ("seed", "index", "key_slot")) or
                (item["family"], item["mode"]) != (family, "i2v")):
            raise ValueError("Frozen writer case differs from primary manifest")
    last = args.runs / writers["last"]["run"]
    check_writer(last, writers["last"], sample)
    case = (last / "case.json").read_bytes()
    key = args.state / "keys" / f"{sample['key_slot']:02}.key"
    message = args.state / "messages" / (sample["id"] + ".bin")
    payload = message.read_bytes()
    if (key.read_bytes() != (last / "secret.key").read_bytes() or len(payload) != 64 or
            not np.array_equal(np.unpackbits(np.frombuffer(payload, dtype=np.uint8)),
                               np.load(last / "message.npy", allow_pickle=False))):
        raise ValueError("State and LAST run use different keys or messages")
    settings = writers["lfg-c"]["settings"]
    if settings != {k: plan["selected_lfg_c"][k] for k in ("lfg_alpha", "lfg_final_steps")}:
        raise ValueError("LFG-C settings differ from calibration selection")
    folder = args.runs / writers["lfg-c"]["run"]
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "controlled-writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        dest = folder / "case.json"
        if dest.exists() and dest.read_bytes() != case:
            raise ValueError("Existing LFG-C case differs from LAST")
        if not dest.exists():
            temp = folder / "case.tmp"
            temp.write_bytes(case)
            temp.replace(dest)
        match_codebook(last, folder)
        common = ["--family", family, "--model-dir", str(args.model)]
        subprocess.run([sys.executable, "-m", "last.smoke", *common, "--mode", "i2v",
                        "--method", "lfg-c", "--case", str(dest), "--output", str(folder),
                        "--key", str(key), "--message", str(message),
                        "--lfg-alpha", str(settings["lfg_alpha"]),
                        "--lfg-final-steps", str(settings["lfg_final_steps"])], check=True)
        check_writer(folder, writers["lfg-c"], sample)
        match_codebook(last, folder)
        subprocess.run([sys.executable, "-m", "last.evaluate", *common, "--run", str(folder),
                        "--video-id", sample["id"]], check=True)


if __name__ == "__main__":
    main()
