"""Recompute paired prompt-cluster intervals for an audited LAST/LFG primary prefix."""
import argparse
import hashlib
import json
from pathlib import Path

from last.cluster_intervals import summarize
from last.data import validate
from last.report import CONDITIONS
from last.robustness_table import collect_disjoint


def compare(report, manifest, manifest_sha, additional_reports=()):
    validate(manifest)
    planned = manifest["samples"]
    reports = [report, *additional_reports]
    ids = [sample for item in reports for sample in item["sample_ids"]]
    selected = set(ids)
    if any(item["manifest_sha256"] != manifest_sha or item["planned_videos_per_method"] != len(planned)
           for item in reports):
        raise ValueError("Reports differ from the frozen manifest")
    if not additional_reports and ids != [s["id"] for s in planned[:len(ids)]]:
        raise ValueError("Expected a prefix of the specified frozen manifest")
    clusters = {s["id"]: hashlib.sha256(s["prompt"].strip().encode()).hexdigest()
                for s in planned if s["id"] in selected}
    if not ids or len(clusters) != len(ids):
        raise ValueError("Unknown or repeated sample IDs")
    groups = collect_disjoint(reports)
    pipelines = {(family, mode) for family, mode, _ in groups}
    if len(pipelines) != 1 or {method for _, _, method in groups} != {"last", "lfg"}:
        raise ValueError("Expected one pipeline with LAST and LFG")
    family, mode = pipelines.pop()
    by_cell = {(method, condition): [] for method in ("last", "lfg") for condition in CONDITIONS}
    rows = [row for item in reports for row in item["audited_observations"]]
    for row in rows:
        if (row["family"], row["mode"]) != (family, mode) or row["map_seed"] != 0:
            raise ValueError("Observation belongs to another primary condition")
        by_cell[row["method"], row["condition"]].append(row)
    results = []
    for condition in CONDITIONS:
        first, second = (by_cell[m, condition] for m in ("last", "lfg"))
        stats = summarize(first, clusters, (0,), second)
        for method, rows in (("last", first), ("lfg", second)):
            cell = groups[family, mode, method][condition]
            actual = (len(rows), sum(r["correct_bits"] for r in rows),
                      sum(r["correct_bits"] == 512 for r in rows))
            if actual != (cell["completed"], cell["correct_bits"], cell["exact_messages"]):
                raise ValueError("Aggregate disagrees with its per-video observations")
        lfg_bits = {row["video_id"]: row["correct_bits"] for row in second}
        pairs = [(row["correct_bits"], lfg_bits[row["video_id"]]) for row in first]
        bit_wins = dict(last=sum(a > b for a, b in pairs), tied=sum(a == b for a, b in pairs),
                        lfg=sum(a < b for a, b in pairs))
        exact = dict(both=sum(a == b == 512 for a, b in pairs),
                     last_only=sum(a == 512 and b < 512 for a, b in pairs),
                     lfg_only=sum(a < 512 and b == 512 for a, b in pairs),
                     neither=sum(max(a, b) < 512 for a, b in pairs))
        results.append(dict(condition=condition, **stats, paired_bit_wins=bit_wins, paired_exact_messages=exact))
    return dict(family=family, mode=mode, videos=len(ids), planned_videos=len(planned),
                full_benchmark=len(ids) == len(planned), manifest_sha256=manifest_sha,
                difference="LAST minus LFG, in units of proportion", conditions=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--additional-report", type=Path, action="append", default=[],
                        help="Include another disjoint set of paired manifest IDs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = args.manifest.read_bytes()
    data = args.report.read_bytes()
    additional = [path.read_bytes() for path in args.additional_report]
    result = compare(json.loads(data), json.loads(manifest), hashlib.sha256(manifest).hexdigest(),
                     [json.loads(blob) for blob in additional])
    if additional:
        result["additional_report_sha256"] = [hashlib.sha256(blob).hexdigest() for blob in additional]
    result["report_sha256"] = hashlib.sha256(data).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
