"""Score both marked videos against each unmarked reference on matched cases."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from compare_references import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    seen = set()
    pipeline = None
    for path in args.report:
        report = json.loads(path.read_bytes())
        group = report["family"], report["mode"], report["manifest_sha256"]
        if pipeline is not None and pipeline != group:
            raise ValueError("Mixed pipeline or manifest")
        pipeline = group
        arms = report["observations"]
        ids = report["sample_ids"]
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("Overlapping samples")
        seen.update(ids)
        indexed = {}
        for method in ("last", "lfg"):
            indexed[method] = {r["video_id"]: r for r in arms[method]}
            if len(arms[method]) != len(ids) or set(indexed[method]) != set(ids):
                raise ValueError("Unpaired fidelity observations")
        for sample in ids:
            files = {}
            for method in indexed:
                folder = args.root / group[0] / group[1] / method / sample
                for kind in ("reference", "marked"):
                    video = folder / (kind + ".mp4")
                    if not video.resolve().is_relative_to(args.root.resolve()):
                        raise ValueError("Video outside primary run directory")
                    if hashlib.sha256(video.read_bytes()).hexdigest() != indexed[method][sample][kind + "_sha256"]:
                        raise ValueError(f"Changed {method} {sample} {kind}")
                    files[method, kind] = video
            reference_difference = compare(files["last", "reference"], files["lfg", "reference"])
            scores = {}
            for reference in indexed:
                scores[reference] = {}
                for method in indexed:
                    diff = compare(files[method, "marked"], files[reference, "reference"])
                    rmse = diff["rmse_8bit"]
                    psnr = 20 * math.log10(255 / rmse) if rmse else None
                    own = indexed[method][sample]["psnr_db"]
                    if method == reference and ((psnr is None) != (own is None)
                                                or (psnr is not None and abs(psnr - own) > 0.001)):
                        raise ValueError("Own-reference PSNR differs from archived score")
                    scores[reference][method] = psnr
            rows.append(dict(video_id=sample, reference_rmse_8bit=reference_difference["rmse_8bit"],
                             psnr_db_by_reference=scores))
    print(json.dumps(dict(family=pipeline[0], mode=pipeline[1], manifest_sha256=pipeline[2],
                          observations=rows), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
