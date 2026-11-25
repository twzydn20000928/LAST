"""Check the 20 development conditioning images against decoded frame zero."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image
from last.development import validate_development
from last.development_case import build
from last.video import load_mp4


def audit(root, development, primary):
    raw = development.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw)
    validate_development(manifest, json.loads(primary.read_bytes()))
    samples = manifest["samples"]
    groups = []
    for i in range(0, len(samples), 4):
        folder = root / f"prompt-{i // 4:02d}"
        cases = [build(manifest, s["id"], "i2v", digest, folder) for s in samples[i:i+4]]
        receipt = json.loads((folder / "receipt.json").read_bytes())
        video = folder / "reference.mp4"
        if hashlib.sha256(video.read_bytes()).hexdigest() != receipt["reference_sha256"]:
            raise ValueError(f"Conditioning video changed: {folder.name}")
        frames = load_mp4(video)
        if len(frames) != 65 or any(f.size != (512, 512) for f in frames):
            raise ValueError(f"Unexpected decoded video geometry: {folder.name}")
        with Image.open(folder / "input.png") as image:
            if image.size != frames[0].size or image.convert("RGB").tobytes() != frames[0].convert("RGB").tobytes():
                raise ValueError(f"Conditioning PNG differs from the decoded first frame: {folder.name}")
        groups.append(dict(prompt_index=i // 4, video_ids=[c["video_id"] for c in cases],
                           generation_seed=receipt["seed"], reference_sha256=receipt["reference_sha256"],
                           image_sha256=receipt["image_sha256"]))
    return dict(manifest_sha256=digest, verified_images=len(groups), assigned_samples=len(samples), groups=groups)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--development", type=Path, default=Path("configs/development_manifest.json"))
    p.add_argument("--primary", type=Path, default=Path("configs/primary_manifest.json"))
    a = p.parse_args()
    print(json.dumps(audit(a.root, a.development, a.primary), indent=2))
