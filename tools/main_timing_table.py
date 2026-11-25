"""Render main Table 3 from paired generation and clean/drop extraction receipts."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from last.timing_summary import check_drop_frames, check_timed_frames
from last.paired_timing import checked_measured_pairs


METHODS = ("sigmark", "videoshield", "videomark", "lfg", "last")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def seconds(value):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0, "Invalid duration")
    return value


def check_received_frames(attack, video_id, condition):
    if condition == "clean":
        require(attack.get("frames") == 65 and attack.get("attack_map") is None,
                "Expected the full 65-frame clean input")
    else:
        check_drop_frames(attack, video_id)


def render(index):
    spec = json.loads(index.read_bytes())
    require(set(spec["methods"]) == set(METHODS), "Expected five timing methods")
    common_case = None
    evidence = {}

    def read(path):
        data = (index.parent / path).read_bytes()
        evidence[path] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    lines = ["| Method | Generation (s) | Watermark overhead (s) | Clean extraction (s) | Drop extraction (s) |",
             "|---|---:|---:|---:|---:|"]
    for method in METHODS:
        files = spec["methods"][method]
        g = read(files["generation"])
        case = read(files["case"])
        require(case["video_id"] == spec["video_id"] and g["case_sha256"] == evidence[files["case"]]
                and case["seed"] == g["seed"], "Generation case mismatch")
        identity = (g["case_sha256"], g["family"], g["mode"], g["gpu"])
        if common_case is None:
            common_case = identity
        require(common_case == identity and g["gpu"] in ("L40", "NVIDIA L40"), "Different case, pipeline or GPU")
        require((g["status"], g["protocol"], g["method"]) == ("completed", "main", method), "Generation mismatch")
        pairs = checked_measured_pairs(g, 2)
        require(g.get("decoded_frame_counts") == [65] * 8,
                "Each reference and marked generation must decode 65 frames in both warmup and measured pairs")
        marked = [seconds(p["marked_seconds"]) for p in pairs]
        overhead = [t - seconds(p["reference_seconds"]) for t, p in zip(marked, pairs)]
        values = [mean(marked), mean(overhead)]
        for condition in ("clean", "drop"):
            r = read(files[condition])
            attack = read(files[condition + "_attack"])
            require((r["status"], r["protocol"], r["method"], r["family"], r["mode"], r["gpu"]) ==
                    ("completed", "main", method, *identity[1:]), "Extraction timing mismatch")
            require((attack["status"], attack["video_id"], attack["method"], attack["condition"], attack["map_seed"]) ==
                    ("completed", spec["video_id"], method, condition, 0), "Attack identity mismatch")
            check_received_frames(attack, spec["video_id"], condition)
            check_timed_frames(r, attack["frames"])
            require(r["received_sha256"] == attack["received_sha256"] and len(r["received_sha256"]) == 64,
                    "Timed video differs from evaluation")
            if condition == "clean":
                marked_hash = attack["received_sha256"]
            require(attack["source_sha256"] == marked_hash, "Different source MP4")
            if method in ("sigmark", "videoshield", "videomark"):
                require(r["temporal"] == (condition == "drop"), "Incorrect temporal recovery mode")
            require(r["warmups"] == r["repeats"] == len(r["seconds"]) == 2, "Expected two measured reads")
            values.append(mean(seconds(t) for t in r["seconds"]))
        lines.append("| " + method + " | " + " | ".join(f"{v:.2f}" for v in values) + " |")
    return "\n".join(lines) + "\n", evidence


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    table, evidence = render(args.index)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "table3.md").write_text(table, encoding="utf-8")
    (args.output / "inputs.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
