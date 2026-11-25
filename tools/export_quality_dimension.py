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


def verify_dimension(manifest_path, inputs, dimension):
    manifest = read(manifest_path)
    validate(manifest)
    expected = {}
    for sample in manifest["samples"]:
        if sample["dimension"] == dimension:
            expected.setdefault(sample["prompt"], []).append(sample)
    if not expected:
        raise ValueError("Unknown dimension")
    coverage_file = inputs / "coverage.json"
    coverage = read(coverage_file)
    meta = inputs / (dimension + ".json")
    rows = read(meta)
    if digest(manifest_path) != coverage["manifest_sha256"]:
        raise ValueError("Inputs differ from the primary manifest")
    if len(rows) != len(expected) or {r["prompt_en"] for r in rows} != set(expected):
        raise ValueError("Scoring inputs do not cover the assigned prompts")
    videos = {v["path"]: v["video_id"] for v in coverage["videos"]}
    for row in rows:
        planned = sorted(expected[row["prompt_en"]], key=lambda s: s["replicate"])
        if [videos[p] for p in row["video_list"]] != [s["id"] for s in planned]:
            raise ValueError("Scoring videos differ from the assigned seeds")
    hashes = verify_inputs(rows, coverage)
    return coverage, rows, videos, hashes


def export(manifest_path, inputs, scores):
    receipt_path, raw_path = scores / "receipt.json", scores / "official_result.json"
    receipt = read(receipt_path)
    if receipt["status"] != "completed":
        raise ValueError("Incomplete official score")
    dimension = receipt["dimension"]
    coverage, rows, videos, hashes = verify_dimension(manifest_path, inputs, dimension)
    if (digest(inputs/(dimension+".json")) != receipt["metadata_sha256"]
            or digest(inputs/"coverage.json") != receipt["coverage_sha256"]):
        raise ValueError("Inputs differ from the scored questions or coverage")
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
    for name in ("manifest", "inputs"):
        parser.add_argument("--" + name, type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scores", type=Path)
    mode.add_argument("--check-inputs", metavar="DIMENSION")
    mode.add_argument("--match-units", type=Path, help="Match prepared videos to an existing public scoring-unit report")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.match_units:
        if args.output:
            parser.error("--output is only used when exporting completed scores")
        from quality_units_table import recount
        units = read(args.match_units)
        summary = recount(args.manifest, [args.match_units])
        dimension = units["dimension"]
        coverage, _, videos, hashes = verify_dimension(args.manifest, args.inputs, dimension)
        current = {videos[path]: sha for path, sha in hashes.items()}
        scored = {v["video_id"]: v["mp4_sha256"] for unit in units["units"] for v in unit["videos"]}
        if current != scored or any(summary[k] != coverage[k] for k in ("family", "mode", "method")):
            raise ValueError("Prepared videos or pipeline differ from the published scoring units")
        print(json.dumps(dict(dimension=dimension, method=coverage["method"], matched_videos=len(current),
                              valid_units=units["valid_units"], mean=units["mean"])))
        raise SystemExit(0)
    if args.check_inputs:
        if args.output:
            parser.error("--output is only used when exporting completed scores")
        coverage, rows, _, hashes = verify_dimension(args.manifest, args.inputs, args.check_inputs)
        print(json.dumps(dict(dimension=args.check_inputs, method=coverage["method"], prompts=len(rows),
                              verified_videos=len(hashes))))
        raise SystemExit(0)
    if not args.output:
        parser.error("--scores requires --output")
    result = export(args.manifest, args.inputs, args.scores)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
