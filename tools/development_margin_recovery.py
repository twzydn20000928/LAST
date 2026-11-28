"""Compute supplementary Section I exact-message sensitivity from development runs."""
import argparse
import json
from pathlib import Path
from statistics import mean

from last.development import validate_development
from plot_margin_sweep import audit_cells, export_public_cells, load_public_cells, read


def summarize_exact(cells, ids, strengths, attacks):
    observed = sorted({name for name, _ in cells})
    if not observed or set(cells) != {(name, mu) for name in observed for mu in strengths}:
        raise ValueError("Each included video must have every frozen margin")
    rows = []
    for mu in strengths:
        exact = {a: sum(cells[name, mu][0][a] == 512 for name in observed) for a in attacks}
        bit_counts = {attack: sum(cells[name, mu][0][attack] for name in observed) for attack in attacks}
        trials = len(observed)*len(attacks)
        rows.append(dict(mu=mu, exact_messages_by_attack=exact, exact_messages=sum(exact.values()),
                         correct_bits_by_attack=bit_counts, total_bits_per_attack=512 * len(observed),
                         video_attack_trials=trials, observed_mean_attack_mrr=sum(exact.values())/trials,
                         mean_psnr_db=mean(cells[name, mu][1] for name in observed)))
    return dict(sample_ids=observed, completed_videos=len(observed), planned_videos=len(ids),
                complete=set(observed) == set(ids), rows=rows)


def completed_entries(root, configs):
    """Select only fully paired cases; audit_cells verifies all selected files."""
    samples = read(configs / "development_manifest.json")["samples"]
    strengths = read(configs / "paper_v1.json")["margin_sweep"]["mu"]
    entries = []
    for sample in samples:
        name = sample["id"]
        folders = [Path(name) / f"mu-{mu:g}" for mu in strengths]
        # Imported default-strength cases may have quality before their attacks.
        def finished(folder):
            quality = root / folder / "quality.json"
            last_attack = root / folder / "attacks" / "clip.json"
            if not quality.is_file() or not last_attack.is_file():
                return False
            return read(last_attack)["status"] != "running"

        if all(finished(folder) for folder in folders):
            entries.extend(dict(video_id=name, run=folder.as_posix()) for folder in folders)
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--index", type=Path)
    source.add_argument("--cells", type=Path)
    source.add_argument("--completed-root", type=Path, help="Audit fully paired cases from an ongoing sweep")
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--export-cells", type=Path, help="Write release-ready per-video counts and quality measurements to a new JSON file")
    parser.add_argument("--plot", type=Path, help="Save the development recovery and fidelity curves")
    args = parser.parse_args()
    validate_development(read(args.configs/"development_manifest.json"), read(args.configs/"primary_manifest.json"))
    if args.completed_root:
        entries = completed_entries(args.completed_root, args.configs)
        data = audit_cells(entries, args.completed_root, args.configs, all_development=True)
    elif args.index:
        data = audit_cells(read(args.index), args.index.parent, args.configs, all_development=True)
    else:
        data = load_public_cells(args.cells, args.configs, all_development=True)
    summary = summarize_exact(*data)
    if args.export_cells:
        export_public_cells(args.export_cells, data[0])
    if args.plot:
        import matplotlib.pyplot as plt
        rows = summary["rows"]
        margins = [row["mu"] for row in rows]
        fig, (recovery, fidelity) = plt.subplots(1, 2, figsize=(9, 3.5), constrained_layout=True)
        recovery.plot(margins, [100 * row["correct_bits_by_attack"]["drop"] / row["total_bits_per_attack"]
                                for row in rows], "o-", label="Correct bits after random deletion")
        recovery.plot(margins, [100 * row["observed_mean_attack_mrr"] for row in rows],
                      "s--", label="Exact messages across six attacks")
        recovery.set(ylabel="Recovery (%)", ylim=(0, 100))
        recovery.legend(fontsize=8)
        fidelity.plot(margins, [row["mean_psnr_db"] for row in rows], "o-", color="#A04E23")
        fidelity.set(ylabel="Mean PSNR (dB)")
        for axis in (recovery, fidelity):
            axis.set(xlabel="Embedding margin μ", xticks=margins)
            axis.grid(axis="y", alpha=0.25)
        fig.suptitle(f"Write strength on {summary['completed_videos']} of {summary['planned_videos']} development videos")
        fig.savefig(args.plot, dpi=160)
        plt.close(fig)
    print(json.dumps(summary, indent=2, allow_nan=False))
