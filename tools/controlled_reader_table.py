"""Render Table 12 shared-fusion counts from separately audited case exports."""
import argparse
import hashlib
import json
from pathlib import Path
import re


READERS = ("received", "calibrated_energy", "ccta", "oracle")
CONDITIONS = ("clean", "drop", "compression")


def render(paths, manifest, primary_paths=None):
    manifest_bytes = manifest.read_bytes()
    samples = {s["id"] for s in json.loads(manifest_bytes)["samples"]}
    if len(samples) != 400:
        raise ValueError("Expected the 400-video primary manifest")
    cells, cohorts = {}, {}
    primary_inputs = {}
    if primary_paths:
        from paired_oracle_table import load_blind_slices

        primary = load_blind_slices(primary_paths, manifest)
        if primary["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest():
            raise ValueError("Primary and controlled manifests differ")
        for row in primary["audited_observations"]:
            if row["mode"] == "i2v" and row["status"] == "completed" and row["map_seed"] == 0:
                key = row["family"], row["method"], row["video_id"], row["condition"]
                if key in primary_inputs:
                    raise ValueError(f"Duplicate primary observation: {key}")
                primary_inputs[key] = row["video_sha256"]
    protocol = None
    for path in paths:
        case = json.loads(path.read_bytes())
        video, writer = case["video_id"], case["writer"]
        if video not in samples or writer not in ("last", "lfg-c") or case["family"] not in ("hunyuan", "wan22"):
            raise ValueError(f"Unexpected primary case: {path}")
        cohort = cohorts.setdefault(writer, set())
        if video in cohort:
            raise ValueError(f"Duplicate case: {writer}/{video}")
        cohort.add(video)
        readers = {r["reader"] for r in case["rows"]}
        if not readers or not readers <= set(READERS) or case["complete_reader_set"] is not (readers == set(READERS)):
            raise ValueError(f"Inconsistent reader set: {path}")
        calibration = case.get("calibration_sha256")
        if "calibrated_energy" in readers and not re.fullmatch("[0-9a-f]{64}", calibration or ""):
            raise ValueError(f"Missing calibration fingerprint: {path}")
        identity = (case["family"], case["source_sha256"], readers, calibration)
        if protocol is None:
            protocol = identity
        if identity != protocol:
            raise ValueError("Use separate tables for different models, source revisions, reader sets or calibrations")
        remaining = {(r, c) for r in readers for c in CONDITIONS}
        received = {}
        for row in case["rows"]:
            r, c, n = row["reader"], row["condition"], row["correct_bits"]
            if (r, c) not in remaining:
                raise ValueError(f"Duplicate or unexpected observation: {path}")
            remaining.remove((r, c))
            if (type(n) is not int or not 0 <= n <= 512 or row["total_bits"] != 512
                    or row["exact_message"] is not (n == 512) or row["blind"] is not (r != "oracle")):
                raise ValueError(f"Invalid controlled measurement: {path}")
            sha = row["received_sha256"]
            if not re.fullmatch("[0-9a-f]{64}", sha) or received.setdefault(c, sha) != sha:
                raise ValueError(f"Readers used different videos for {video}/{c}")
            if primary_paths and primary_inputs.get((case["family"], writer, video, c)) != sha:
                raise ValueError(f"Controlled MP4 differs from the primary input or is missing: {video}/{c}")
            cells.setdefault((writer, r, c), []).append(n)
        if remaining:
            raise ValueError(f"Missing controlled measurements: {path}")
    if len(cohorts) == 2 and cohorts["last"] != cohorts["lfg-c"]:
        raise ValueError("Writer comparison requires identical sample IDs")
    lines = [f"{protocol[0]} I2V | shared-fusion measurements | {len(next(iter(cohorts.values())))}/400 videos per supplied writer",
             "", "| Writer | Reader | Condition | Correct bits | Bit accuracy | Exact messages |",
             "|---|---|---|---:|---:|---:|"]
    for writer in sorted(cohorts):
        for reader in READERS:
            for condition in CONDITIONS:
                counts = cells.get((writer, reader, condition))
                if counts:
                    n, total = sum(counts), 512 * len(counts)
                    label = "oracle (assisted)" if reader == "oracle" else reader
                    lines.append(f"| {writer} | {label} | {condition} | {n}/{total} | {n/total:.2%} | {counts.count(512)}/{len(counts)} |")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+", type=Path)
    parser.add_argument("--primary", type=Path, action="append",
                        help="Verify every received MP4 against the primary results for the same writer")
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    args = parser.parse_args()
    print(render(args.cases, args.manifest, args.primary))
