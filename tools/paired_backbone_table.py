"""Render the published LAST text-to-video comparison on ten matched prompt IDs."""
from paired_videomark_table import CONDITIONS, load_counts


def main():
    samples = tuple(f"paper-{i:03d}" for i in range(10))
    hunyuan = load_counts("hunyuan_t2v_last_first50.json", "audited_observations", samples)
    wan = load_counts("wan22_t2v_last_first10.json", "audited_observations", samples)
    print("| Condition | Hunyuan correct bits | Wan2.2 correct bits | Hunyuan exact | Wan2.2 exact |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for condition in CONDITIONS:
        left = [hunyuan[sample, condition] for sample in samples]
        right = [wan[sample, condition] for sample in samples]
        print(f"| {condition} | {sum(left)} | {sum(right)} | {left.count(512)} | {right.count(512)} |")


if __name__ == "__main__":
    main()
