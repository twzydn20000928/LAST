"""Recount one shared-fusion comparison and export only public measurements."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(run, evaluation):
    path = evaluation / "receipt.json"
    report = json.loads(path.read_bytes())
    readers = report["readers"]
    known = {"received", "calibrated_energy", "ccta", "oracle"}
    conditions = ("clean", "drop", "compression")
    if (report["status"] != "completed" or not readers or not set(readers) <= known
            or len(readers) != len(set(readers)) or tuple(report["conditions"]) != conditions
            or report["complete_reader_set"] is not (set(readers) == known)):
        raise ValueError("Incomplete or inconsistent controlled evaluation")
    for name, fingerprint in report["input_sha256"].items():
        if digest(Path(name)) != fingerprint:
            raise ValueError("Controlled evaluation input changed")
    truth_file = run / "message.npy"
    if report["input_sha256"].get(str(truth_file.resolve())) != digest(truth_file):
        raise ValueError("Wrong source run")
    truth = np.load(truth_file, allow_pickle=False)
    expected = {(c, r) for c in conditions for r in readers}
    rows = []
    calibration_evidence = {}
    for row in report["rows"]:
        c, r = row["condition"], row["reader"]
        if (c, r) not in expected:
            raise ValueError("Duplicate or unplanned observation")
        expected.remove((c, r))
        kind = "ccta" if r == "calibrated_energy" else r
        cache = evaluation / f"{c}-{kind}-features" / "receipt.json"
        output = evaluation / f"{c}-{r}-read"
        receipt = output / "receipt.json"
        prediction = output / "decoded-private.json"
        video = run / "marked.mp4" if c == "clean" else run / "attacks" / f"{c}.mp4"
        read = json.loads(receipt.read_bytes())
        if (digest(cache) != row["feature_receipt_sha256"] or digest(receipt) != row["extraction_receipt_sha256"]
                or digest(prediction) != read["decoded_sha256"] or digest(video) != row["received_sha256"]
                or read["status"] != "completed" or read["reader"] != r
                or read["blind"] is not (r != "oracle") or row["blind"] is not read["blind"]
                or read["input_sha256"].get(str(video.resolve())) != row["received_sha256"]
                or read["input_sha256"].get(str(cache.resolve())) != row["feature_receipt_sha256"]):
            raise ValueError(f"Unmatched controlled read: {c}/{r}")
        if r == "calibrated_energy":
            standard = (video, run / "codes.pt", cache, cache.parent / "features.npy", cache.parent / "nodes.json")
            extra = set(read["input_sha256"]) - {str(item.resolve()) for item in standard}
            if len(extra) != 1:
                raise ValueError("Expected one calibration input in the calibrated read receipt")
            calibration_path = extra.pop()
            fingerprint = read["input_sha256"][calibration_path]
            if (report["input_sha256"].get(calibration_path) != fingerprint
                    or calibration_evidence.setdefault("calibration_sha256", fingerprint) != fingerprint):
                raise ValueError("Controlled reads used different calibrations")
        bits = np.asarray(json.loads(prediction.read_bytes())["information_bits"])
        if any(a.shape != (512,) or not np.isin(a, (0, 1)).all() for a in (bits, truth)):
            raise ValueError("Expected 512 information bits")
        correct = int(np.count_nonzero(bits == truth))
        if row["correct_bits"] != correct or row["total_bits"] != 512 or row["exact_message"] is not (correct == 512):
            raise ValueError("Controlled prediction recount mismatch")
        rows.append({key: row[key] for key in ("condition", "reader", "blind", "correct_bits", "total_bits",
                                              "exact_message", "received_sha256", "feature_receipt_sha256",
                                              "extraction_receipt_sha256")})
    if expected:
        raise ValueError("Missing controlled reads")
    return dict(video_id=json.loads((run / "attacks/clean.json").read_bytes())["video_id"],
                family=report["family"], writer=report["writer"], complete_reader_set=report["complete_reader_set"],
                evaluation_sha256=digest(path), source_sha256=report["source_sha256"], rows=rows, **calibration_evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "evaluation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = export(args.run, args.evaluation)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
