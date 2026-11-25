"""Compare decoded LAST/LFG reference pairs from an audited fidelity report."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
from compare_references import compare


def collect(report, root):
    samples = report["sample_ids"]
    observations = []
    paths = {}
    for method in ("last", "lfg"):
        rows = report["observations"][method]
        if sorted(row["video_id"] for row in rows) != sorted(set(samples)) or len(samples) != len(set(samples)):
            raise ValueError("Expected one reference per method and sample")
        for row in rows:
            sample = row["video_id"]
            path = (root / report["family"] / report["mode"] / method / sample / "reference.mp4").resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Reference outside run directory")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != row["reference_sha256"]:
                raise ValueError(f"Reference differs from fidelity measurement: {method}/{sample}")
            paths[method, sample] = path, digest
    for sample in samples:
        left, left_hash = paths["last", sample]
        right, right_hash = paths["lfg", sample]
        observations.append(dict(video_id=sample, last_reference_sha256=left_hash,
                                 lfg_reference_sha256=right_hash, opencv_version=cv2.__version__,
                                 **compare(left, right)))
    return dict(family=report["family"], mode=report["mode"],
                scope="Between-method unmarked reference differences", observations=observations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(json.loads(args.report.read_bytes()), args.root), indent=2))
