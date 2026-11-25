"""Count exact deletion recoveries in the eight primary Hunyuan I2V key slots."""
import argparse
import hashlib
import json
from pathlib import Path

from last.cluster_intervals import observations
from last.data import validate


def collect(manifest_bytes, report):
    manifest = json.loads(manifest_bytes)
    validate(manifest)
    samples = {s["id"]: s["key_slot"] for s in manifest["samples"]}
    ids = report["sample_ids"]
    if (report["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()
            or not ids or len(ids) != len(set(ids)) or not set(ids) <= samples.keys()):
        raise ValueError("Invalid manifest or sample identifiers")
    rows = [row for row in report["audited_observations"]
            if (row["family"], row["mode"], row["method"], row["condition"])
            == ("hunyuan", "i2v", "last", "drop")]
    checked = observations(rows, ids, (0,))
    cell, = [c for c in report["cells"] if (c["family"], c["mode"], c["method"], c["condition"])
             == ("hunyuan", "i2v", "last", "drop")]
    if (len(rows), sum(r["correct_bits"] for r in rows), sum(r["correct_bits"] == 512 for r in rows)) != (
            cell["completed"], cell["correct_bits"], cell["exact_messages"]):
        raise ValueError("Deletion totals disagree with the audited observations")
    blocks = []
    for slot in range(8):
        exact = [int(v[1]) for (video, _), v in checked.items() if samples[video] == slot]
        blocks.append(dict(key_slot=slot, completed=len(exact), planned=50, exact_messages=sum(exact),
                           observed_mrr=sum(exact)/len(exact) if exact else None))
    complete = set(ids) == samples.keys()
    rates = [b["observed_mrr"] for b in blocks]
    return dict(completed=len(ids), planned=len(samples), exact_messages=cell["exact_messages"],
                full_key_range=[min(rates), max(rates)] if complete else None, blocks=blocks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/primary_manifest.json"))
    args = parser.parse_args()
    print(json.dumps(collect(args.manifest.read_bytes(), json.loads(args.report.read_bytes())), indent=2))
