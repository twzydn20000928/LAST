"""Compare decoded LAST/LFG reference pairs from an audited fidelity report."""
import argparse
import hashlib
import json
from pathlib import Path

def collect(report, root, settings_only=False):
    samples = report["sample_ids"]
    observations = []
    paths = {}
    arms = {}
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
            if settings_only:
                folder = path.parent
                raw = (folder / "receipt.json").read_bytes()
                g = json.loads(raw)
                case = (folder / "case.json").read_bytes()
                if (g["method"] != method or g["family"] != report["family"] or g["mode"] != report["mode"]
                        or g["status"] != "completed" or g["marked_sha256"] != row["marked_sha256"]
                        or g["case_sha256"] != hashlib.sha256(case).hexdigest()
                        or json.loads(case)["video_id"] != sample
                        or hashlib.sha256((folder / "quality.json").read_bytes()).hexdigest() != row["quality_receipt_sha256"]):
                    raise ValueError(f"Generation differs from fidelity observation: {method}/{sample}")
                fields = ("seed", "source_sha256", "settings", "hardware", "offload", "memory_limit_gib", "case_sha256")
                arms[method, sample] = dict({k: g[k] for k in fields},
                    model_directory_name=Path(g["model_directory"]).name, reference_sha256=digest,
                    generation_receipt_sha256=hashlib.sha256(raw).hexdigest())
    if settings_only:
        return dict(scope="Recorded settings of paired unmarked reference generations",
                    observations=[dict(video_id=s, arms={m: arms[m, s] for m in ("last", "lfg")}) for s in samples])
    import cv2
    from compare_references import compare
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
    parser.add_argument("--settings-only", action="store_true", help="Compare recorded generation settings and file identity")
    args = parser.parse_args()
    print(json.dumps(collect(json.loads(args.report.read_bytes()), args.root, args.settings_only), indent=2))
