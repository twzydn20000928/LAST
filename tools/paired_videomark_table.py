"""Compare the first seven published Hunyuan T2V cases under each attack."""
import json
from paired_lfg_table import CONDITIONS, RESULTS, count_bits

SAMPLES = tuple(f"paper-{i:03d}" for i in range(7))


def load_counts(filename, field):
    report = json.loads((RESULTS / filename).read_bytes())
    counts = {}
    for row in report[field]:
        sample = row["video_id"]
        if sample not in SAMPLES:
            continue
        key = sample, row["condition"]
        if key in counts or key[1] not in CONDITIONS:
            raise ValueError(f"Unexpected observation in {filename}: {key}")
        counts[key] = count_bits(row)
    if len(counts) != len(SAMPLES) * len(CONDITIONS):
        raise ValueError(f"Incomplete sample coverage in {filename}")
    return counts


def main():
    last = load_counts("hunyuan_t2v_last_first50.json", "audited_observations")
    videomark = load_counts("hunyuan_t2v_videomark_first7.json", "observations")
    print("| Condition | LAST correct bits | VideoMark correct bits | LAST exact | VideoMark exact |")
    print("|---|---:|---:|---:|---:|")
    for condition in CONDITIONS:
        a = [last[sample, condition] for sample in SAMPLES]
        b = [videomark[sample, condition] for sample in SAMPLES]
        print(f"| {condition} | {sum(a)}/3584 | {sum(b)}/3584 | {a.count(512)}/7 | {b.count(512)}/7 |")


if __name__ == "__main__":
    main()
