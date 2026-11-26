"""Prepare private Table 12 inputs from a verified replay of legacy attack files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from last.reextract_evidence import verified_rows, sha
from last.temporal import attack_map


def prepare(run, replay, source, output):
    if output.exists():
        raise FileExistsError(output)
    verified = verified_rows(run, replay, source)
    replay_receipt = replay / "receipt.json"
    replay_bytes = replay_receipt.read_bytes()
    parents = {row["condition"]: row for row in json.loads(replay_bytes)["rows"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        view = Path(temporary) / "view"
        (view / "attacks").mkdir(parents=True)
        for filename in ("case.json", "receipt.json", "marked.mp4", "message.npy", "codes.pt"):
            (view / filename).symlink_to((run / filename).resolve(strict=True))
        sample = json.loads((run / "case.json").read_bytes())["video_id"]
        for condition in ("clean", "drop", "compression"):
            evidence = verified[condition]
            old = (run / "attacks" / (condition + ".json")).read_bytes()
            fingerprint = hashlib.sha256(old).hexdigest()
            row = json.loads(old)
            mapping = attack_map(sample, condition) if condition == "drop" else None
            if (fingerprint != parents[condition]["prior_receipt_sha256"]
                    or row["video_id"] != sample or row["condition"] != condition
                    or row["status"] != "completed" or row["attack_map"] != mapping
                    or row["frames"] != (len(mapping) if mapping is not None else 65)
                    or row.get("map_seed", 0) != 0
                    or hashlib.sha256(replay_bytes).hexdigest() != evidence["reextraction_receipt_sha256"]):
                raise ValueError(f"Unmatched replay provenance for {sample}/{condition}")
            if row.get("received_sha256") not in (None, evidence["received_sha256"]):
                raise ValueError(f"Conflicting historical MP4 digest for {sample}/{condition}")
            row.update(received_sha256=evidence["received_sha256"],
                       prior_receipt_sha256=fingerprint, reextraction_receipt_sha256=evidence["reextraction_receipt_sha256"])
            if condition != "clean":
                name = condition + ".mp4"
                (view / "attacks" / name).symlink_to((run / "attacks" / name).resolve(strict=True))
            (view / "attacks" / (condition + ".json")).write_text(json.dumps(row, indent=2))
        if sha(replay_receipt) != hashlib.sha256(replay_bytes).hexdigest():
            raise ValueError("Replay changed during preparation")
        view.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "replay", "source", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    prepare(args.run, args.replay, args.source, args.output)
