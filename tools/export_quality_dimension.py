"""Recount an official dimension and export its scores without host paths."""
import argparse
import hashlib
import json
from pathlib import Path

from last.data import validate
from last.quality_score import summarize, verify_inputs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def export(manifest_path, inputs, scores):
    manifest = read(manifest_path)
    validate(manifest)
    receipt_path, raw_path = scores / "receipt.json", scores / "official_result.json"
    receipt = read(receipt_path)
    dimension = receipt["dimension"]
    expected = {}
    for sample in manifest["samples"]:
        if sample["dimension"] == dimension:
            expected.setdefault(sample["prompt"], []).append(sample)
    if not expected or receipt["status"] != "completed":
        raise ValueError("Unknown dimension or incomplete official score")
    coverage_file = inputs / "coverage.json"
    coverage = read(coverage_file)
    meta = inputs / (dimension + ".json")
    rows = read(meta)
    if (digest(manifest_path) != coverage["manifest_sha256"] or digest(meta) != receipt["metadata_sha256"]
            or digest(coverage_file) != receipt["coverage_sha256"]):
        raise ValueError("Inputs differ from the scored manifest or questions")
    if len(rows) != len(expected) or {r["prompt_en"] for r in rows} != set(expected):
        raise ValueError("Scoring inputs do not cover the assigned prompts")
    videos = {v["path"]: v["video_id"] for v in coverage["videos"]}
    for row in rows:
        planned = sorted(expected[row["prompt_en"]], key=lambda s: s["replicate"])
        if [videos[p] for p in row["video_list"]] != [s["id"] for s in planned]:
            raise ValueError("Scoring videos differ from the assigned seeds")
    hashes = verify_inputs(rows, coverage)
    if hashes != receipt["videos_sha256"]:
        raise ValueError("Current videos differ from extraction-time video hashes")
    raw = read(raw_path)
    summary = summarize(raw, rows, dimension)
    if any(summary[k] != receipt[k] for k in summary):
        raise ValueError("Official per-unit scores disagree with scoring receipt")
    values = {v["video_path"]: float(v["video_results"]) for v in raw[1]}
    units = []
    for row in rows:
        paths = row["video_list"]
        groups = [paths] if dimension == "Diversity" else [[p] for p in paths]
        for group in groups:
            units.append(dict(score=values[group[0]], videos=[
                dict(video_id=videos[p], mp4_sha256=hashes[p]) for p in group]))
    return dict(family=coverage["family"], mode=coverage["mode"], method=coverage["method"],
                dimension=dimension, manifest_sha256=coverage["manifest_sha256"], **summary,
                receipt_sha256=digest(receipt_path), raw_sha256=digest(raw_path), units=units)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "inputs", "scores", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = export(args.manifest, args.inputs, args.scores)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
