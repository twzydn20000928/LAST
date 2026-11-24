"""Compute matched clean consistency scores for one completed LAST case."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from last.carriers import codebook
from last.feature_cache import load, sha
from last.hypothesis_statistics import clean_consistency_pairs, clean_energy_pairs, matched_summary
from last.oracle_reader import oracle_nodes


def score(run, cache, calibration_path=None):
    features, nodes, record = load(cache, run / "marked.mp4")
    attack_path = run / "attacks/clean.json"
    attack = json.loads(attack_path.read_bytes())
    generation = json.loads((run / "receipt.json").read_bytes())
    if (generation["method"] != "last" or generation["family"] != record["family"]
            or generation["marked_sha256"] != record["video_sha256"]):
        raise ValueError("Generation receipt differs from clean LAST input")
    if (nodes != oracle_nodes(list(range(65))) or record["frames"] != 65
            or attack["video_id"] != run.name or attack["method"] != "last"
            or attack["status"] != "completed" or attack["condition"] != "clean"
            or attack["attack_map"] is not None
            or attack["source_sha256"] != record["video_sha256"]
            or attack["received_sha256"] != record["video_sha256"]):
        raise ValueError("Expected verified clean LAST video with all 16 intact groups")
    saved = torch.load(run / "codes.pt", weights_only=True, map_location="cpu").numpy()
    np.testing.assert_allclose(codebook((run / "secret.key").read_bytes()), saved,
                               atol=1e-7, rtol=1e-6)
    correlations = np.einsum("gd,hbd->ghb", features, saved, optimize=True)
    pairs = clean_consistency_pairs(correlations)
    ids = [f"{run.name}/{r['window_start']}/{r['wrong_group_start']}" for r in pairs]
    summary = matched_summary([r["correct"] for r in pairs], [r["wrong"] for r in pairs], ids, ids)
    result = dict(video_id=run.name, family=record["family"], mode=generation["mode"], method="last",
                scope="Single clean-video consistency diagnostic",
                pairs=pairs, summary=summary, mp4_sha256=record["video_sha256"],
                cache_receipt_sha256=sha(cache / "receipt.json"), attack_receipt_sha256=sha(attack_path))
    if calibration_path is not None:
        config = Path(__file__).resolve().parents[1] / "configs"
        calibration = json.loads(calibration_path.read_bytes())
        protocol = calibration["shared_protocol"]
        if (calibration.get("acquisition_audited") is not True
                or calibration["development_manifest_sha256"] != sha(config / "development_manifest.json")
                or calibration["primary_manifest_sha256"] != sha(config / "primary_manifest.json")
                or protocol["family"] != record["family"]
                or protocol["vae"] != record["vae_files_sha256"]):
            raise ValueError("Require audited development calibration for the same manifests, backbone and VAE")
        energy = clean_energy_pairs(correlations, calibration)
        result["energy_pairs"] = energy
        result["calibration_sha256"] = sha(calibration_path)
        result["energy_summary"] = {
            field: matched_summary([r[field + "_correct"] for r in energy],
                                   [r[field + "_wrong"] for r in energy], ids, ids)
            for field in ("raw", "calibrated")}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--calibration", type=Path, help="All-80 development output from last.null_fit")
    args = parser.parse_args()
    print(json.dumps(score(args.run, args.cache, args.calibration), indent=2, allow_nan=False))
