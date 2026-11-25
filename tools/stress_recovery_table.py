"""Recompute the recovery columns of supplementary Table 15 from audited counts."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from last.cluster_intervals import summarize
from paired_oracle_table import load_blind_report


ATTACKS = ("drop10", "drop20", "drop30", "drop45", "duplicate30", "natural30",
           "interpolate30", "drop30_crf28")
SEEDS = tuple(range(5))


def indexed_reports(index):
    reports = []
    for entry in json.loads(index.read_bytes())["sources"]:
        report = json.loads((index.parent / entry["file"]).read_bytes())
        requested = set(entry["attacks"])
        rows = [r for r in report.get("rows", [report]) if r["attack"] in requested]
        if not requested or {r["attack"] for r in rows} != requested:
            raise ValueError(f"Missing indexed attack in {entry['file']}")
        reports.append(dict(report, rows=rows))
    return reports


def collect(manifest, reports):
    samples = manifest["samples"]
    clusters = {sample["id"]: sample["prompt"].strip() for sample in samples}
    if len(clusters) != len(samples) or not clusters:
        raise ValueError("Expected a nonempty manifest with distinct sample IDs")
    counts = {attack: {} for attack in ATTACKS}
    pipelines = set()
    donor_protocols = set()
    donor_by_video = {}
    for report in reports:
        pipelines.add(tuple(report[field] for field in ("family", "mode", "method", "reader_commit")))
        video = report["video_id"]
        for row in report.get("rows", [report]):
            attack, seed = row["attack"], row["seed"]
            if (video not in clusters or row.get("video_id", video) != video or attack not in counts
                    or type(seed) is not int or seed not in SEEDS or (video, seed) in counts[attack]):
                raise ValueError("Unexpected or duplicate video, attack or map seed")
            bits = row["correct_bits"]
            if (type(bits) is not int or not 0 <= bits <= 512 or row["total_bits"] != 512
                    or row["exact_message"] is not (bits == 512)):
                raise ValueError("Inconsistent information-bit or exact-message count")
            if attack == "natural30":
                donor_protocols.add(row.get("canonical_donor_plan_sha256", row.get("donor_plan_sha256")))
                donor = row["donor_sha256"]
                if donor_by_video.setdefault(video, donor) != donor:
                    raise ValueError("The same target has different donor videos across map seeds")
            counts[attack][video, seed] = bits
    if len(pipelines) != 1:
        raise ValueError("Expected records from a single generation pipeline, method and reader revision")
    if len(donor_protocols) > 1:
        raise ValueError("Mixed natural-insertion donor assignment protocols")

    cells = []
    for attack, trials in counts.items():
        exact = sum(bits == 512 for bits in trials.values())
        cell = dict(attack=attack, completed=len(trials), planned=len(clusters)*len(SEEDS),
                    correct_bits=sum(trials.values()), total_bits=512*len(trials), exact_messages=exact,
                    mean_mrr=None, ci95=None, map_range=None)
        if trials and cell["completed"] == cell["planned"]:
            rows = [dict(video_id=v, map_seed=s, status="completed", correct_bits=n, total_bits=512)
                    for (v, s), n in trials.items()]
            stats = summarize(rows, clusters, SEEDS)
            rates = [sum(trials[v, seed] == 512 for v in clusters)/len(clusters) for seed in SEEDS]
            cell.update(mean_mrr=stats["message_recovery"], ci95=stats["message_recovery_ci95"],
                        map_range=[min(rates), max(rates)])
        cells.append(cell)
    return cells


def alignment_counts(reports):
    """Aggregate audited reader routes after collect has validated the trials."""
    grouped = defaultdict(list)
    for report in reports:
        for row in report.get("rows", [report]):
            grouped[row["attack"]].append(row)
    result = {}
    for attack, rows in grouped.items():
        lengths = []
        fallback = no_evidence = intact = correct = 0
        for row in rows:
            route = row["route"]
            if route == "energy_spacing":
                lengths.append(1)
                fallback += 1
            elif route == "no_evidence":
                no_evidence += 1
            elif route == "ccta":
                counts = row["alignment"]
                chains = row["chain_lengths"]
                if (not chains or any(type(n) is not int or n < 2 for n in chains)
                        or sum(chains) != row["groups"] or row["groups"] != counts["selected"]
                        or not 0 <= counts["correct"] <= counts["intact_selected"] <= counts["selected"]):
                    raise ValueError("Inconsistent selected group counts")
                lengths.append(sum(chains))
                intact += counts["intact_selected"]
                correct += counts["correct"]
            else:
                raise ValueError(f"Unexpected primary reader route: {route}")
        result[attack] = dict(
            observed_trials=len(rows), fallback_trials=fallback, no_evidence_trials=no_evidence,
            fallback_fraction=fallback / len(rows),
            median_selected_groups=median(lengths) if not no_evidence else None,
            ccta_intact_selected=intact, ccta_correct_group=correct,
            group_accuracy=correct / intact if intact and not fallback and not no_evidence else None,
        )
    return result


def compare_primary_deletions(primary, reports, manifest_digest):
    if primary["manifest_sha256"] != manifest_digest:
        raise ValueError("Primary and stress manifests differ")
    family, mode, method = (reports[0][k] for k in ("family", "mode", "method"))
    indexed = {}
    for row in primary["audited_observations"]:
        if (row["family"], row["mode"], row["method"], row["condition"], row["map_seed"]) != (
                family, mode, method, "drop", 0):
            continue
        video = row["video_id"]
        if video in indexed or row["status"] != "completed" or row["total_bits"] != 512:
            raise ValueError(f"Invalid primary deletion observation for {video}")
        indexed[video] = row
    comparison = []
    for report in reports:
        for edit in report.get("rows", [report]):
            if edit["attack"] != "drop30" or edit["seed"] != 0:
                continue
            video = report["video_id"]
            if video not in indexed or indexed[video]["video_sha256"] != edit["received_sha256"]:
                raise ValueError(f"No matching primary received MP4 for {video}")
            comparison.append(dict(video_id=video, received_sha256=edit["received_sha256"],
                                   primary_correct_bits=indexed[video]["correct_bits"],
                                   stress_correct_bits=edit["correct_bits"]))
    if not comparison:
        raise ValueError("No drop30 seed-zero observations to compare")
    return comparison


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    p.add_argument("--alignment", action="store_true", help="Include observed alignment columns from exports made with --alignment")
    p.add_argument("--primary", type=Path, help="Match drop30 seed zero against an audited primary report by received MP4")
    sources = p.add_mutually_exclusive_group(required=True)
    sources.add_argument("--reports", type=Path, nargs="+")
    sources.add_argument("--index", type=Path, help="Report paths and attack names relative to the index file")
    a = p.parse_args()
    read = lambda path: json.loads(path.read_bytes())
    reports = indexed_reports(a.index) if a.index else [read(f) for f in a.reports]
    cells = collect(read(a.manifest), reports)
    if a.alignment:
        counts = alignment_counts(reports)
        for cell in cells:
            cell["observed_alignment"] = counts.get(cell["attack"])
    if a.primary:
        primary = load_blind_report(a.primary, a.manifest)
        comparison = compare_primary_deletions(primary, reports, hashlib.sha256(a.manifest.read_bytes()).hexdigest())
        next(cell for cell in cells if cell["attack"] == "drop30")["primary_seed_zero_comparison"] = comparison
    print(json.dumps(cells, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
