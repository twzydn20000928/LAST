"""Assign unmarked donor videos using only frozen sample metadata."""
import argparse
import hashlib
import json
from pathlib import Path

from .data import validate


def plan(manifest_path):
    data = manifest_path.read_bytes()
    manifest = json.loads(data)
    validate(manifest)
    groups = {}
    for sample in manifest["samples"]:
        prompt = " ".join(sample["prompt"].casefold().split())
        groups.setdefault(prompt, []).append(sample["id"])
    ordered = [video for group in groups.values() for video in group]
    shift = max(map(len, groups.values()))
    donors = ordered[shift:] + ordered[:shift]
    if shift * 2 > len(ordered):
        raise ValueError("Cannot assign a unique different-prompt donor to every sample")
    return dict(manifest_sha256=hashlib.sha256(data).hexdigest(),
                reference_method="last", offset=shift, assignments=dict(zip(ordered, donors)))


def resolve(plan_path, manifest_path, reference_root, video_id):
    frozen = json.loads(plan_path.read_bytes())
    if frozen != plan(manifest_path):
        raise ValueError("Donor assignment differs from the frozen manifest rule")
    donor_id = frozen["assignments"][video_id]
    directory = reference_root / donor_id
    generation = json.loads((directory / "receipt.json").read_bytes())
    case_bytes = (directory / "case.json").read_bytes()
    case = json.loads(case_bytes)
    sample = next(s for s in json.loads(manifest_path.read_bytes())["samples"] if s["id"] == donor_id)
    if (generation["status"] != "completed" or generation["method"] != frozen["reference_method"]
            or generation["case_sha256"] != hashlib.sha256(case_bytes).hexdigest()
            or case["video_id"] != donor_id or case["seed"] != sample["seed"] or case["prompt"] != sample["prompt"]):
        raise ValueError("Donor run differs from the assigned primary case")
    path = directory / "reference.mp4"
    quality = json.loads((directory / "quality.json").read_bytes())
    if (quality["marked_sha256"] != generation["marked_sha256"]
            or quality["reference_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()):
        raise ValueError("Donor reference differs from its paired quality record")
    return path, donor_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = plan(args.manifest)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
