"""Export paired reader counts after verifying archived videos and codebooks."""
import argparse
import hashlib
import json
from pathlib import Path

from last.ablation_summary import CONDITIONS, VARIANTS, summarize


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(index_path, subset_path):
    plan = json.loads(subset_path.read_bytes())["ablation_i2v_30"]
    index = json.loads(index_path.read_bytes())
    if not index or set(index) - set(plan):
        raise ValueError("Expected at least one sample from the frozen subset")
    rows, public = [], []
    for video, paths in sorted(index.items()):
        run = index_path.parent / paths["run"]
        receipts = index_path.parent / paths["readers"]
        marked, codebook = digest(run / "marked.mp4"), digest(run / "codes.pt")
        for condition in CONDITIONS:
            received = marked if condition == "clean" else digest(run / "attacks" / (condition + ".mp4"))
            for variant in VARIANTS:
                path = receipts / f"{condition}-{variant}.json"
                data = path.read_bytes()
                row = json.loads(data)
                actual = tuple(row[k] for k in ("video_id", "condition", "variant", "status",
                                                "source_sha256", "video_sha256", "codes_sha256", "writer_method"))
                if actual != (video, condition, variant, "completed", marked, received, codebook, "last"):
                    raise ValueError(f"Unmatched or incomplete reader receipt: {path}")
                rows.append(row)
                public.append(dict(video_id=video, condition=condition, variant=variant,
                                   correct_bits=row["correct_bits"], received_sha256=received,
                                   receipt_sha256=hashlib.sha256(data).hexdigest()))
    summary = summarize(rows, plan)
    return dict(ordered_subset=plan, planned_videos=len(plan),
                scope="Reader rerun on archived minimum-margin writer inputs",
                observations=public, cells=summary["cells"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--subsets", type=Path, default=Path("configs/paper_subsets.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = export(args.index, args.subsets)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write("\n")
