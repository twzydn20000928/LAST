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


def matched_edits(manifest, report, frames, removed, seed):
    from primary_message_tables import summaries
    summaries(report, manifest)
    ids = report["sample_ids"]
    result = {}
    bits = {}
    for edit in ("drop", "clip"):
        bits[edit] = {r["video_id"]: r["correct_bits"] for r in report["observations"][edit]}
        counts = []
        by_pair = {True: [], False: []}
        for video in ids:
            mapping = attack_map(video, edit, seed, frames, removed)
            if len(mapping) != frames-removed or mapping != sorted(set(mapping)):
                raise ValueError("Expected equal frame count and preserved order")
            counts.append(geometry(mapping, frames))
            by_pair[counts[-1][1]].append(bits[edit][video])
        values = list(bits[edit].values())
        result[edit] = dict(**summarize(counts), retained_frames=frames-removed,
                            intact_groups=sum(n for n, _ in counts), total_source_groups=len(ids)*16,
                            correct_bits=sum(values), total_bits=len(ids)*512,
                            exact_messages=values.count(512),
                            by_adjacent_pair=[dict(adjacent_pair=pair, videos=len(observed),
                                                  correct_bits=sum(observed), exact_messages=observed.count(512))
                                              for pair, observed in by_pair.items() if observed])
    differences = [bits["clip"][s]-bits["drop"][s] for s in ids]
    result["paired_clip_minus_drop"] = dict(more_correct_bits=sum(x>0 for x in differences),
                                             tied=sum(x==0 for x in differences),
                                             fewer_correct_bits=sum(x<0 for x in differences))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    parser.add_argument("--report", type=Path, help="Also stratify the audited Hunyuan I2V LAST deletion observations")
    parser.add_argument("--matched-edits", type=Path, help="Compare random and contiguous removal from an original message report")
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
    if args.matched_edits:
        report = json.loads(args.matched_edits.read_bytes())
        if report["manifest_sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("Primary manifest mismatch")
        result["matched_edits"] = matched_edits(manifest, report, frames, attacks["temporal_count"], seed)
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
