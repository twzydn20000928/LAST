"""Audit and render Tables 10 and 11 on a fixed cohort of Hunyuan I2V LAST runs."""
import argparse
import json
from pathlib import Path

from last.data import validate
from last.message_outcomes import render_tables, summarize
from last.report import CONDITIONS
from primary_deletion_errors import collect, digest


def summaries(evidence, manifest):
    planned = [s["id"] for s in manifest["samples"]]
    cohort = evidence["sample_ids"]
    if not cohort or len(cohort) != len(set(cohort)) or not set(cohort) <= set(planned):
        raise ValueError("Invalid cohort")
    result = {}
    for condition in CONDITIONS:
        counts = evidence["observations"][condition]
        if sorted(r["video_id"] for r in counts) != sorted(cohort):
            raise ValueError(f"Unpaired or incomplete cohort for {condition}")
        rows = [dict(r, status="completed", total_bits=512, exact_message=r["correct_bits"] == 512) for r in counts]
        result[condition] = summarize(rows, planned)
    return dict(family="hunyuan", mode="i2v", method="last", map_seed=0, conditions=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--root", type=Path)
    mode.add_argument("--report", type=Path)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--cohort", type=Path, help="Frozen audited deletion report for acquisition")
    selection.add_argument("--range", dest="index_range", type=int, nargs=2, metavar=("FIRST", "STOP"),
                           help="Audit every sample in this manifest slice (exclusive upper index)")
    parser.add_argument("--export", type=Path, help="New public JSON file for acquisition")
    parser.add_argument("--aggregate", type=Path, help="New aggregate JSON for last.clean_table and last.robustness_table")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    validate(manifest)
    if args.root:
        if not (args.cohort or args.index_range) or not args.export:
            parser.error("Acquisition requires --cohort or --range, plus --export")
        if args.cohort:
            prior = json.loads(args.cohort.read_bytes())
            if prior["manifest_sha256"] != digest(args.manifest):
                raise ValueError("Cohort manifest mismatch")
            ids = [r["video_id"] for r in prior["observations"]]
            selection_fields = dict(cohort_sha256=digest(args.cohort))
        else:
            first, stop = args.index_range
            if not 0 <= first < stop <= len(manifest["samples"]):
                parser.error("Requested range falls outside the primary manifest")
            ids = [s["id"] for s in manifest["samples"][first:stop]]
            selection_fields = dict(manifest_index_range=[first, stop])
        evidence = dict(manifest_sha256=digest(args.manifest), **selection_fields, sample_ids=ids, observations={})
        for c in CONDITIONS:
            evidence["observations"][c] = collect(args.root, manifest, c, set(ids))["observations"]
        if args.cohort and evidence["observations"]["drop"] != prior["observations"]:
            raise ValueError("Deletion receipts changed since the cohort was frozen")
    else:
        evidence = json.loads(args.report.read_bytes())
        if evidence["manifest_sha256"] != digest(args.manifest):
            raise ValueError("Evidence manifest mismatch")
    tables = summaries(evidence, manifest)
    if args.root:
        with args.export.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, indent=2, allow_nan=False)
            stream.write("\n")
    if args.aggregate:
        cells = []
        for condition, summary in tables["conditions"].items():
            bits = 512 * summary["completed"]
            cells.append(dict(family="hunyuan", mode="i2v", method="last", condition=condition,
                              expected=summary["expected"], completed=summary["completed"], total_bits=bits,
                              correct_bits=bits-summary["post_bch_error_bits"], exact_messages=summary["exact_messages"],
                              complete=summary["complete"], final_bit_accuracy=summary["final_bit_accuracy"]))
        aggregate = dict(artifact_verification=True, manifest_sha256=evidence["manifest_sha256"],
                         message_report_sha256=digest(args.export if args.root else args.report),
                         scope="Counts from acquisition-verified original MP4 receipts; public replay recomputes counts",
                         cells=cells)
        with args.aggregate.open("x", encoding="utf-8") as stream:
            json.dump(aggregate, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(render_tables(tables))
