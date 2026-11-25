"""Print shared-fusion extraction commands for a frozen Table 12 writer block."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys


def check_writer(folder, item, sample):
    case_file = folder / "case.json"
    case_bytes = case_file.read_bytes()
    case = json.loads(case_bytes)
    generation = json.loads((folder / "receipt.json").read_bytes())
    if (generation.get("status") != "completed" or
            generation.get("case_sha256") != hashlib.sha256(case_bytes).hexdigest() or
            any(generation.get(k) != item[k] for k in ("family", "mode", "method", "seed")) or
            (case["video_id"], case["prompt"], case["seed"]) !=
            (sample["id"], sample["prompt"], sample["seed"]) or
            ("key_slot" in case and case["key_slot"] != sample["key_slot"])):
        raise ValueError(f"Generated video differs from planned sample: {folder}")
    if hashlib.sha256(Path(case["image"]).read_bytes()).hexdigest() != sample["image_sha256"]:
        raise ValueError(f"Conditioning image differs from planned sample: {folder}")
    # c1f2f694's LAST writer calls embed(z, codes, signs) without any overrides.
    defaults = {}
    if item["method"] == "last" and generation.get("source_sha256") == (
            "feeabdbc0e639184dbf896cd25786fa59a377205a77a6d115609dc0e06467c7c"):
        defaults = dict(mu=.5, fixed_target=False, uniform_profile=False)
    for key, value in item["settings"].items():
        field = "mu" if key == "margin" else key
        if generation.get(field, defaults.get(field)) != value:
            raise ValueError(f"Generated video has a different {field}: {folder}")


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
            check_writer(runs / relative, item, sample)
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
