"""Decode a trusted SIGMark run's saved initial latent directly on CPU."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from last.baseline_extract import validate_prediction
from last.baseline_probe import load_class


def diagnose(run, upstream, manifest_path):
    generation = json.loads((run / "receipt.json").read_bytes())
    clean = json.loads((run / "attacks/clean-extract/receipt.json").read_bytes())
    manifest = json.loads(manifest_path.read_bytes())
    state = run / "maintained_private.pkl"
    state_sha = hashlib.sha256(state.read_bytes()).hexdigest()
    if (generation["method"] != "sigmark" or clean["method"] != "sigmark"
            or generation["upstream_commit"] != manifest["commit"]
            or clean["upstream_commit"] != manifest["commit"]
            or clean["status"] != "completed_extraction" or clean["temporal"]
            or clean["state_sha256"] != state_sha):
        raise ValueError("Expected a completed ordinary SIGMark read with its recorded state")
    marked_sha = hashlib.sha256((run / "marked.mp4").read_bytes()).hexdigest()
    if (generation["status"] not in ("completed", "completed_generation_only")
            or generation["video_sha256"] != marked_sha or clean["video_sha256"] != marked_sha):
        raise ValueError("Generation and clean extraction MP4 differ")
    if generation.get("state_sha256", state_sha) != state_sha:
        raise ValueError("Generation state changed")
    latent_path = run / "initial_private.pt"
    latent = torch.load(latent_path, map_location="cpu", weights_only=True)
    if tuple(latent.shape) != (1, 16, 17, 64, 64):
        raise ValueError("Expected the 65-frame primary latent geometry")
    truth = np.unpackbits(np.frombuffer((run / "message.bin").read_bytes(), dtype=np.uint8))
    if truth.size != 512:
        raise ValueError("Expected 512 information bits")
    decoded = (run / "attacks/clean-extract/decoded.bin").read_bytes()
    if len(decoded) != 64:
        raise ValueError("Expected 512 clean extraction bits")
    clean_bits = np.unpackbits(np.frombuffer(decoded, dtype=np.uint8))
    clean_count = int(np.count_nonzero(clean_bits == truth))
    score = json.loads((run / "attacks/clean.json").read_bytes())
    if (score["status"] != "completed" or score["correct_bits"] != clean_count
            or score["source_sha256"] != marked_sha or score["received_sha256"] != marked_sha
            or score["state_sha256"] != state_sha or score["total_bits"] != 512):
        raise ValueError("Ordinary clean score differs from the saved artifacts")
    cls = load_class("sigmark", upstream, manifest)
    reader = cls(video_h=512, video_w=512, video_f=65, latent_c=16,
                 vae_scale_factor_spatial=8, vae_scale_factor_temporal=4,
                 ch_factor=2, hw_factor=8, fr_factor=16, batch_size=1,
                 seed=0, dtype=torch.bfloat16, device="cpu", maintained_info_path=str(state))
    with torch.inference_mode():
        prediction = validate_prediction(reader.extract_watermark(latent))
    return dict(video_id=run.name, scope="Saved initial latent, direct CPU decoding",
                correct_bits=int(np.count_nonzero(prediction == truth)), total_bits=512,
                clean_video_correct_bits=clean_count,
                generation_state_digest_recorded="state_sha256" in generation,
                upstream_commit=manifest["commit"], latent_dtype=str(latent.dtype),
                latent_sha256=hashlib.sha256(latent_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Trusted local generation directory")
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("configs/sigmark_source_manifest.json"))
    args = parser.parse_args()
    print(json.dumps(diagnose(args.run, args.upstream, args.manifest), indent=2))
