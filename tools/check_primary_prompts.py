"""Reconstruct the ordered primary prompt assignments from pinned SIGMark assets."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from last.data import validate


def check(manifest, metadata, prompt_dir):
    validate(manifest)
    if manifest["source"]["revision"] != metadata["commit"]:
        raise ValueError("Primary and metadata revisions differ")
    assignments = []
    slots = []
    for entry in sorted(metadata["files"], key=lambda e: e["path"]):
        path = PurePosixPath(entry["path"])
        if path.parent != PurePosixPath("prompt_set/VBench2_aug_prompt") or path.suffix != ".txt":
            continue
        raw = (prompt_dir / path.name).read_bytes()
        header = f"blob {len(raw)}\0".encode()
        if hashlib.sha1(header + raw).hexdigest() != entry["sha"]:
            raise ValueError(f"Prompt list differs from upstream revision: {path.name}")
        lines = raw.decode("utf-8").splitlines()
        count, repeats = (3, 20) if path.stem == "Diversity" else (5, 4)
        stride = len(lines) // count
        if not stride:
            raise ValueError(f"Too few source prompts: {path.name}")
        for slot in range(count):
            line = slot * stride
            prompt = lines[line].strip()
            slots.append(dict(dimension=path.stem, line_index=line, first_sample=len(assignments)))
            assignments.extend((path.stem, prompt, rep) for rep in range(repeats))
    rows = manifest["samples"]
    if len(assignments) != len(rows):
        raise ValueError("Reconstructed and declared sample counts differ")
    for row, expected in zip(rows, assignments):
        if (row["dimension"], row["prompt"], row["replicate"]) != expected:
            raise ValueError(f"Source prompt or repetition differs for {row['id']}")
    return dict(revision=metadata["commit"], verified_samples=len(rows), prompt_slots=slots)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--metadata", type=Path, default=Path("configs/quality_metadata_manifest.json"))
    args = parser.parse_args()
    print(json.dumps(check(json.loads(args.manifest.read_bytes()), json.loads(args.metadata.read_bytes()),
                           args.prompt_dir), indent=2))
