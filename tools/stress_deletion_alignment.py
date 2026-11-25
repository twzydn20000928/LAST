"""Compare intact source groups with CCTA selections after frozen frame deletions."""
import argparse
import json
from pathlib import Path

from deletion_group_survival import geometry
from last.temporal import attack_map
from stress_recovery_table import collect

REMOVED = {"drop10": 10, "drop20": 20, "drop30": 30, "drop45": 45, "drop30_crf28": 30}


def summarize(manifest, reports):
    collect(manifest, reports)
    cells = {}
    for report in reports:
        for r in report["rows"]:
            name = r["attack"]
            if name not in REMOVED:
                continue
            mapping = attack_map(report["video_id"], "drop", r["seed"], 65, REMOVED[name])
            if len(mapping) != r["received_frames"]:
                raise ValueError("Unexpected deletion map length")
            available, _ = geometry(mapping)
            cell = cells.setdefault(name, dict(trials=0, ccta_trials=0, available_on_ccta=0,
                                              selected=0, intact_selected=0, correct=0))
            cell["trials"] += 1
            if r["route"] != "ccta":
                continue
            a = r["alignment"]
            if not (0 <= a["correct"] <= a["intact_selected"] <= available
                    and a["selected"] == sum(r["chain_lengths"]) == r["groups"]
                    and a["selected"] == a["false_window_selected"] + a["intact_selected"]
                    and a["intact_selected"] == a["wrong_group_on_intact"] + a["correct"]):
                raise ValueError("Inconsistent saved chain counts")
            cell["ccta_trials"] += 1
            cell["available_on_ccta"] += available
            for field in ("selected", "intact_selected", "correct"):
                cell[field] += a[field]
    return cells


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    p.add_argument("--reports", type=Path, nargs="+", required=True)
    args = p.parse_args()
    read = lambda path: json.loads(path.read_bytes())
    print(json.dumps(summarize(read(args.manifest), [read(p) for p in args.reports]), indent=2))
