"""Compare matched published Hunyuan T2V cases under each primary attack."""
import argparse
import json
from paired_lfg_table import CONDITIONS, RESULTS, count_bits

SAMPLES = tuple(f"paper-{i:03d}" for i in range(20))


def load_counts(filename, field, samples=SAMPLES):
    report = json.loads((RESULTS / filename).read_bytes())
    counts = {}
    for row in report[field]:
        sample = row["video_id"]
        if sample not in samples:
            continue
        key = sample, row["condition"]
        if key in counts or key[1] not in CONDITIONS:
            raise ValueError(f"Unexpected observation in {filename}: {key}")
        counts[key] = count_bits({"total_bits": report.get("information_bits"), **row})
    if len(counts) != len(samples) * len(CONDITIONS):
        raise ValueError(f"Incomplete sample coverage in {filename}")
    return counts


def main(count=37, last_report='hunyuan_t2v_last_first73.json'):
    if not 1 <= count <= 400:
        raise ValueError('Expected a primary prefix of 1 to 400 cases')
    samples = tuple(f"paper-{i:03d}" for i in range(count))
    last = load_counts(last_report, "audited_observations", samples)
    videomark = load_counts(f"hunyuan_t2v_videomark_first{count}.json", "audited_observations", samples)
    print("| Condition | LAST correct bits | VideoMark correct bits | LAST exact | VideoMark exact |")
    print("|---|---:|---:|---:|---:|")
    for condition in CONDITIONS:
        a = [last[sample, condition] for sample in samples]
        b = [videomark[sample, condition] for sample in samples]
        print(f"| {condition} | {sum(a)}/{512 * count} | {sum(b)}/{512 * count} | {a.count(512)}/{count} | {b.count(512)}/{count} |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=37)
    parser.add_argument("--last-report", default="hunyuan_t2v_last_first73.json")
    args = parser.parse_args()
    main(args.count, args.last_report)
