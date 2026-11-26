"""Compare matched LAST and reference units for one official quality dimension."""
import argparse
import json
from pathlib import Path
from statistics import mean

from quality_units_table import recount


def compare(manifest, fidelity, marked, reference):
    records = []
    for path, method in ((marked, "last"), (reference, "reference")):
        recount(manifest, [path], fidelity=fidelity)
        record = json.loads(path.read_bytes())
        if record["method"] != method:
            raise ValueError(f"Expected {method} scoring units in {path}")
        records.append(record)
    left, right = records
    for field in ("manifest_sha256", "family", "mode", "dimension", "unit"):
        if left[field] != right[field]:
            raise ValueError(f"Mismatched {field}")

    def by_sample(record):
        return {tuple(v["video_id"] for v in u["videos"]): u["score"] for u in record["units"]}

    a, b = by_sample(left), by_sample(right)
    if a.keys() != b.keys():
        raise ValueError("Different sets of scoring units")
    differences = [a[k] - b[k] for k in a if a[k] >= 0 and b[k] >= 0]
    return dict(dimension=left["dimension"], unit=left["unit"], expected_pairs=len(a),
                applicable_pairs=len(differences), higher=sum(x > 0 for x in differences),
                equal=differences.count(0), lower=sum(x < 0 for x in differences),
                mean_last_minus_reference=mean(differences) if differences else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    parser.add_argument("--fidelity", type=Path, required=True)
    parser.add_argument("marked", type=Path)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.manifest, args.fidelity, args.marked, args.reference), indent=2, allow_nan=False))
