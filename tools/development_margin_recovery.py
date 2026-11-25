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
        trials = len(observed)*len(attacks)
        rows.append(dict(mu=mu, exact_messages_by_attack=exact, exact_messages=sum(exact.values()),
                         video_attack_trials=trials, observed_mean_attack_mrr=sum(exact.values())/trials,
                         mean_psnr_db=mean(cells[name, mu][1] for name in observed)))
    return dict(sample_ids=observed, completed_videos=len(observed), planned_videos=len(ids),
                complete=set(observed) == set(ids), rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--index", type=Path)
    source.add_argument("--cells", type=Path)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--export-cells", type=Path, help="Write release-ready per-video counts and quality measurements to a new JSON file")
    args = parser.parse_args()
    validate_development(read(args.configs/"development_manifest.json"), read(args.configs/"primary_manifest.json"))
    if args.index:
        data = audit_cells(read(args.index), args.index.parent, args.configs, all_development=True)
    else:
        data = load_public_cells(args.cells, args.configs, all_development=True)
    summary = summarize_exact(*data)
    if args.export_cells:
        export_public_cells(args.export_cells, data[0])
    print(json.dumps(summary, indent=2, allow_nan=False))
