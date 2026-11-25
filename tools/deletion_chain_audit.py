"""Compare blind-selected groups with original frame identities after extraction."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from last.temporal import attack_map


def collect(root, report):
    routes = {}
    support = Counter()
    videos = []
    for sample in report["observations"]:
        name = sample["video_id"]
        raw = (root / "hunyuan" / "i2v" / "last" / name / "attacks" / "drop.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != sample["receipt_sha256"]:
            raise ValueError(f"Changed attack receipt for {name}")
        row = json.loads(raw)
        mapping = attack_map(name, "drop")
        if row["attack_map"] != mapping or row["correct_bits"] != sample["correct_bits"]:
            raise ValueError(f"Primary deletion record differs for {name}")
        route = row["route"]
        arm = routes.setdefault(route, dict(videos=0, exact=0))
        arm["videos"] += 1
        arm["exact"] += int(row["correct_bits"] == 512)
        if route != "ccta":
            continue
        histogram = Counter()
        for c in row["chains"]:
            start, group, length = c["start"], c["first_group"], c["length"]
            if length < 2 or start < 0 or start+4*length > len(mapping) or group < 0 or group+length > 16:
                raise ValueError(f"Invalid chain coordinates for {name}")
            for i in range(length):
                original = mapping[start+4*i:start+4*i+4]
                first = 1+4*(group+i)
                histogram[sum(first <= frame < first+4 for frame in original)] += 1
        if sum(histogram.values()) != row["groups"]:
            raise ValueError(f"Selected length disagrees for {name}")
        support.update(histogram)
        videos.append(dict(video_id=name, correct_bits=row["correct_bits"], support_histogram=histogram))
    return dict(routes=routes, selected_windows=sum(support.values()), support_histogram=support, videos=videos)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = args.report.read_bytes()
    result = collect(args.root, json.loads(report))
    result["report_sha256"] = hashlib.sha256(report).hexdigest()
    print(json.dumps(result, indent=2))
