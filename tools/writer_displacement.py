"""Measure the two writer interventions on the same archived diffusion endpoint."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from last.coding import BCH512
from last.elmc import embed
from last.writer_replay import digest, validate_source


def compare(run):
    source = validate_source(run)
    if source["fixed_target"]:
        raise ValueError("Expected the minimum-margin generation as the shared source")
    fixed = json.loads((run.parent / "fixed-target/receipt.json").read_bytes())
    if fixed["status"] != "completed" or not fixed["fixed_target"]:
        raise ValueError("Require a completed fixed-target replay")
    for field in ("family", "mode", "settings", "seed", "case_sha256", "mu", "uniform_profile"):
        if fixed[field] != source[field]:
            raise ValueError(f"Writer arms disagree on {field}")
    for name in ("endpoint.pt", "codes.pt", "message.npy", "secret.key", "reference.mp4"):
        if digest(run / name) != fixed["source_artifact_sha256"][name]:
            raise ValueError(f"Archived writer input differs from the paired replay: {name}")
    endpoint = torch.load(run / "endpoint.pt", map_location="cpu", weights_only=True).float()
    codes = torch.load(run / "codes.pt", map_location="cpu", weights_only=True)
    message = np.load(run / "message.npy", allow_pickle=False)
    signs = BCH512().encode(message).astype(np.float32) * 2 - 1
    energy = {}
    for name, fixed_target in (("minimum_margin", False), ("fixed_target", True)):
        marked = embed(endpoint, codes, signs, mu=source["mu"], uniform=source["uniform_profile"],
                       fixed_target=fixed_target)
        energy[name] = float((marked.double() - endpoint.double()).square().sum())
    return dict(case_sha256=source["case_sha256"], endpoint_sha256=source["endpoint_sha256"],
                squared_l2=energy, device="cpu", computation="float32 writer; float64 squared distance")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Paired writer minimum-margin directory")
    args = parser.parse_args()
    torch.set_num_threads(2)
    with torch.inference_mode():
        print(json.dumps(compare(args.run), indent=2, allow_nan=False))
