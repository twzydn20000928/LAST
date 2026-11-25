"""Recount dimension and category means from exported official scoring units."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from last.data import validate
from last.quality_report import aggregate, CATEGORIES


def recount(manifest_path, paths):
    manifest = json.loads(manifest_path.read_bytes())
    validate(manifest)
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    dimensions = {}
    pipeline = None
    for path in paths:
        record = json.loads(path.read_bytes())
        identity = record["family"], record["mode"], record["method"]
        if pipeline is None:
            pipeline = identity
        name = record["dimension"]
        if identity != pipeline or record["manifest_sha256"] != manifest_digest or name in dimensions:
            raise ValueError("Expected one pipeline, one manifest and distinct dimensions")
        samples = [s for s in manifest["samples"] if s["dimension"] == name]
        if not samples:
            raise ValueError(f"Unknown dimension: {name}")
        expected = {}
        for s in samples:
            unit = s["prompt"] if name == "Diversity" else s["id"]
            expected.setdefault(unit, []).append(s["id"])
        observed = [tuple(v["video_id"] for v in unit["videos"]) for unit in record["units"]]
        if sorted(observed) != sorted(tuple(ids) for ids in expected.values()):
            raise ValueError(f"Missing or incorrectly grouped observations: {name}")
        values = [u["score"] for u in record["units"]]
        valid = [x for x in values if 0 <= x <= 1]
        if len(valid) + values.count(-1) != len(values):
            raise ValueError(f"Invalid official score: {name}")
        value = mean(valid) if valid else None
        if (len(valid) != record["valid_units"] or len(values) != record["expected_units"]
                or values.count(-1) != record["not_applicable_units"]
                or (value is None) != (record["mean"] is None)
                or (value is not None and not math.isclose(value, record["mean"], abs_tol=1e-12))):
            raise ValueError(f"Unit recount disagrees with exported summary: {name}")
        dimensions[name] = dict(status="completed", mean=value, valid_units=len(valid), full_dimension_inputs=True)
    complete = set(dimensions) == {name for names in CATEGORIES.values() for name in names}
    return dict(pipeline=pipeline, **aggregate(dimensions, complete))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("units", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(recount(args.manifest, args.units), indent=2, allow_nan=False))
