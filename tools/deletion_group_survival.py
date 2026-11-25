"""Count intact source groups under the frozen primary deletion maps."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from last.data import validate
from last.temporal import attack_map


def geometry(mapping, frames=65):
    retained = set(mapping)
    intact = [set(range(start, start+4)) <= retained for start in range(1, frames, 4)]
    return sum(intact), any(a and b for a, b in zip(intact, intact[1:]))


def summarize(counts):
    return dict(videos=len(counts), intact_group_histogram=dict(sorted(Counter(n for n, _ in counts).items())),
                videos_with_intact_adjacent_pair=sum(pair for _, pair in counts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--report", type=Path, help="Also stratify the audited Hunyuan I2V LAST deletion observations")
    args = parser.parse_args()
    raw = (args.configs/"primary_manifest.json").read_bytes()
    manifest = json.loads(raw)
    validate(manifest)
    protocol = json.loads((args.configs/"paper_v1.json").read_bytes())
    frames = protocol["video"]["frames"]
    attacks = protocol["attacks"]
    seed = attacks["primary_map_seed"]
    if frames != 65 or attacks["temporal_count"] != 30:
        raise ValueError("Expected the 65-frame primary deletion experiment")
    groups = {s["id"]: geometry(attack_map(s["id"], "drop", seed, frames, 30), frames)
              for s in manifest["samples"]}
    result = dict(map_seed=seed, planned_maps=summarize(groups.values()))
    if args.report:
        from deletion_by_key import collect
        report = json.loads(args.report.read_bytes())
        collect(raw, report)
        strata = {}
        for row in report["audited_observations"]:
            if (row["family"], row["mode"], row["method"], row["condition"]) != ("hunyuan", "i2v", "last", "drop"):
                continue
            n, pair = groups[row["video_id"]]
            cell = strata.setdefault((n, pair), dict(videos=0, correct_bits=0, total_bits=0, exact_messages=0))
            cell["videos"] += 1
            cell["correct_bits"] += row["correct_bits"]
            cell["total_bits"] += 512
            cell["exact_messages"] += int(row["correct_bits"] == 512)
        result["observed"] = [dict(intact_groups=n, intact_adjacent_pair=pair, **cell)
                              for (n, pair), cell in sorted(strata.items())]
        result["report_sha256"] = hashlib.sha256(args.report.read_bytes()).hexdigest()
    print(json.dumps(result, indent=2))
