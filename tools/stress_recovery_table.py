"""Recompute the recovery columns of supplementary Table 15 from audited counts."""
import argparse
import json
from pathlib import Path

from last.cluster_intervals import summarize


ATTACKS = ("drop10", "drop20", "drop30", "drop45", "duplicate30", "natural30",
           "interpolate30", "drop30_crf28")
SEEDS = tuple(range(5))


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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    p.add_argument("--reports", type=Path, nargs="+", required=True)
    a = p.parse_args()
    read = lambda path: json.loads(path.read_bytes())
    cells = collect(read(a.manifest), [read(f) for f in a.reports])
    print(json.dumps(cells, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
