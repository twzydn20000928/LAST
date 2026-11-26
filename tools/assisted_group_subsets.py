"""Re-read intact and partial original groups separately on a Table 12 deletion input."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from last.controlled_reader import decode_oracle
from last.feature_cache import load, sha
from last.oracle_reader import oracle_nodes
from last.temporal import attack_map


def compare(run, evaluation, case):
    public = json.loads(case.read_bytes())
    row, = [r for r in public["rows"] if r["condition"] == "drop" and r["reader"] == "oracle"]
    cache, read = evaluation / "drop-oracle-features", evaluation / "drop-oracle-read"
    video = run / "attacks/drop.mp4"
    values, nodes, features = load(cache, video)
    if (public["video_id"] != run.name or row["received_sha256"] != features["video_sha256"]
            or row["feature_receipt_sha256"] != sha(cache / "receipt.json")
            or row["extraction_receipt_sha256"] != sha(read / "receipt.json")
            or nodes != oracle_nodes(attack_map(run.name, "drop"))):
        raise ValueError("Cache, true group IDs or source video differ from the controlled case")
    receipt = json.loads((read / "receipt.json").read_bytes())
    codes = run / "codes.pt"
    prediction = read / "decoded-private.json"
    if receipt["input_sha256"][str(codes.resolve())] != sha(codes) or receipt["decoded_sha256"] != sha(prediction):
        raise ValueError("Codebook or original prediction changed")
    truth = np.load(run / "message.npy", allow_pickle=False)
    if truth.shape != (512,) or not np.isin(truth, [0, 1]).all():
        raise ValueError("Expected 512 information bits")
    code = torch.load(codes, map_location="cpu", weights_only=True)
    corr = torch.einsum("nd,gmd->ngm", torch.from_numpy(values).float(), code.float())
    output = {}
    for subset in ("all", "intact", "partial"):
        chosen = [(i, n["group"]) for i, n in enumerate(nodes)
                  if subset == "all" or (n["filled"] == 0) == (subset == "intact")]
        correct = None
        if chosen:
            evidence = torch.stack([corr[i, group] for i, group in chosen])
            bits, _, _ = decode_oracle(evidence, [group for _, group in chosen])
            correct = int((np.asarray(bits) == truth).sum())
            if subset == "all" and (correct != row["correct_bits"] or
                    bits.tolist() != json.loads(prediction.read_bytes())["information_bits"]):
                raise ValueError("All-group prediction differs from the archived controlled read")
        output[subset] = dict(groups=len(chosen), correct_bits=correct)
    return dict(video_id=run.name, case_sha256=sha(case), subsets=output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "evaluation", "case"):
        parser.add_argument("--" + name, required=True, type=Path)
    torch.set_num_threads(2)
    print(json.dumps(compare(**vars(parser.parse_args()))))
