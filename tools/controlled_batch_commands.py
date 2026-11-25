"""Print shared-fusion extraction commands for a frozen Table 12 writer block."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys


def commands(plan, manifest, runs, model, calibration, output):
    samples = json.loads(manifest.read_bytes())["samples"]
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != plan["manifest_sha256"]:
        raise ValueError("Frozen plan uses a different primary manifest")
    readers = ["received", "calibrated_energy", "ccta", "oracle"]
    if (plan["readers"] != readers or plan["conditions"] != ["clean", "drop", "compression"]
            or len(samples) != 400 or len(plan["runs"]) != 2 * len(samples)):
        raise ValueError("Expected the full Table 12 shared-carrier plan")
    family = plan["runs"][0]["family"]
    if family not in ("hunyuan", "wan22"):
        raise ValueError("Unknown video model")
    lines = []
    for method_index, method in enumerate(("last", "lfg-c")):
        settings = (dict(margin=.5, fixed_target=False, uniform_profile=False) if method == "last"
                    else {k: plan["selected_lfg_c"][k] for k in ("lfg_alpha", "lfg_final_steps")})
        for i, sample in enumerate(samples):
            item = plan["runs"][method_index * len(samples) + i]
            relative = f"{family}/i2v/{method}/{sample['id']}"
            if (item["run"] != relative or item["settings"] != settings or
                    (item["index"], item["family"], item["mode"], item["method"], item["video_id"],
                     item["key_slot"], item["seed"]) !=
                    (i, family, "i2v", method, sample["id"], sample["key_slot"], sample["seed"])):
                raise ValueError(f"Writer block differs from the frozen plan at {relative}")
            lines.append(shlex.join([sys.executable, "-m", "last.controlled_evaluate",
                                     "--run", str(runs / relative), "--family", family,
                                     "--model-dir", str(model), "--calibration", str(calibration),
                                     "--output", str(output / relative)]))
    return lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "manifest", "runs", "model", "calibration", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    lines = commands(json.loads(args.plan.read_bytes()), args.manifest, args.runs,
                     args.model, args.calibration, args.output)
    print("set -e")
    print("\n".join(lines))
