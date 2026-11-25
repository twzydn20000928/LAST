"""Compare matched published Hunyuan T2V cases under each primary attack."""
import argparse
import json
from paired_lfg_table import CONDITIONS, RESULTS, count_bits

SAMPLES = tuple(f"paper-{i:03d}" for i in range(20))


def load_counts(filename, field, samples=SAMPLES, *, family="hunyuan", mode="t2v", method="last"):
    report = json.loads((RESULTS / filename).read_bytes())
    if report.get("manifest_sha256") != "348a52a3d122da7d5895e99246b2cc1bd344133b770f32af3363b73249447b58":
        raise ValueError(f"Unexpected primary sample manifest in {filename}")
    if field == "observations":
        if ((family, mode, method) != ("hunyuan", "i2v", "last")
                or report.get("scope") != "First 100 frozen Hunyuan I2V LAST samples"
                or report.get("plan_sha256") != "510122dc3c5f460f99a71bc4a823dea950e550dbc57b5bd636bc8394d9dcd8fb"):
            raise ValueError(f"Unrecognized single-method measurements in {filename}")
    elif field != "audited_observations" or report.get("artifact_verification") is not True:
        raise ValueError(f"Expected an audited primary report in {filename}")
    counts = {}
    for row in report[field]:
        sample = row["video_id"]
        if sample not in samples:
            continue
        if field == "audited_observations" and (row["family"], row["mode"], row["method"], row["status"], row["map_seed"]) != (
                family, mode, method, "completed", 0):
            raise ValueError(f"Unexpected primary comparison arm in {filename}: {sample}")
        key = sample, row["condition"]
        if key in counts or key[1] not in CONDITIONS:
            raise ValueError(f"Unexpected observation in {filename}: {key}")
        counts[key] = count_bits({"total_bits": report.get("information_bits"), **row})
    if len(counts) != len(samples) * len(CONDITIONS):
        raise ValueError(f"Incomplete sample coverage in {filename}")
    return counts


def main(count=38, last_report='hunyuan_t2v_last_first73.json', videomark_report='hunyuan_t2v_videomark_first38.json'):
    if not 1 <= count <= 400:
        raise ValueError('Expected a primary prefix of 1 to 400 cases')
    samples = tuple(f"paper-{i:03d}" for i in range(count))
    last = load_counts(last_report, "audited_observations", samples, method="last")
    videomark = load_counts(videomark_report, "audited_observations", samples, method="videomark")
    print("| Condition | LAST correct bits | VideoMark correct bits | LAST exact | VideoMark exact |")
    print("|---|---:|---:|---:|---:|")
    for condition in CONDITIONS:
        a = [last[sample, condition] for sample in samples]
        b = [videomark[sample, condition] for sample in samples]
        print(f"| {condition} | {sum(a)}/{512 * count} | {sum(b)}/{512 * count} | {a.count(512)}/{count} | {b.count(512)}/{count} |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=38)
    parser.add_argument("--last-report", default="hunyuan_t2v_last_first73.json")
    parser.add_argument("--videomark-report", default="hunyuan_t2v_videomark_first38.json")
    args = parser.parse_args()
    main(args.count, args.last_report, args.videomark_report)
