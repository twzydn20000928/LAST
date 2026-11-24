"""Score the windows in saved CCTA chains against verified stress edit maps."""
import argparse
import json
from pathlib import Path

from last.alignment_metrics import evaluate, stress_source_indices


def score(selection, receipt):
    mapping = stress_source_indices(receipt)
    if selection["route"] != "ccta" or not selection["chains"]:
        raise ValueError("Scoring chain windows requires saved CCTA chains")
    totals = dict(selected=0, intact_selected=0, correct=0, false_window_selected=0, wrong_group_on_intact=0)
    last_end = 0
    for chain in selection["chains"]:
        start, first, length = (chain[k] for k in ("start", "first_group", "length"))
        if (any(type(i) is not int for i in (start, first, length)) or length < 2 or start < last_end
                or first < 0 or first + length > 16 or start + 4*length > len(mapping)):
            raise ValueError("Invalid or overlapping selected chain")
        last_end = start + 4*length
        nodes = [dict(indices=list(range(t, t+4))) for t in range(start, last_end, 4)]
        selected = [dict(candidate=i, group=first+i) for i in range(length)]
        counts = evaluate(nodes, mapping, selected)
        for key in totals:
            totals[key] += counts[key]
    if totals["selected"] != selection["groups"]:
        raise ValueError("Reported selection count disagrees with saved chains")
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selections", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path, nargs="+")
    args = parser.parse_args()
    selections = json.loads(args.selections.read_bytes())
    indexed = {}
    for selection in selections:
        key = selection["evaluation_receipt_sha256"]
        if key in indexed:
            raise ValueError("Duplicate selection receipt")
        indexed[key] = selection
    rows = []
    for path in args.reports:
        report = json.loads(path.read_bytes())
        for row in report.get("rows", [report]):
            selection = indexed.pop(row["evaluation_receipt_sha256"])
            if row["attack"] != selection["attack"]:
                raise ValueError("Attack identity differs")
            receipt = dict(row, video_id=report["video_id"], frames=row["received_frames"])
            rows.append(dict(video_id=receipt["video_id"], attack=row["attack"], seed=row["seed"],
                             chain_lengths=[c["length"] for c in selection["chains"]], **score(selection, receipt)))
    if indexed:
        raise ValueError("Selection receipts without a corresponding edit map")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
