"""Render the published LAST backbone comparison on matched prompt IDs."""
import argparse
from paired_videomark_table import CONDITIONS, load_counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("t2v", "i2v"), default="t2v")
    mode = parser.parse_args().mode
    if mode == "i2v":
        count = 30
        left_file, left_field = "hunyuan_i2v_last_first100_robustness.json", "observations"
        right_file = "wan22_i2v_last_first30.json"
    else:
        count = 10
        left_file, left_field = "hunyuan_t2v_last_first50.json", "audited_observations"
        right_file = "wan22_t2v_last_first10.json"
    samples = tuple(f"paper-{i:03d}" for i in range(count))
    hunyuan = load_counts(left_file, left_field, samples)
    wan = load_counts(right_file, "audited_observations", samples)
    print("| Condition | Hunyuan correct bits | Wan2.2 correct bits | Hunyuan exact | Wan2.2 exact |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for condition in CONDITIONS:
        left = [hunyuan[sample, condition] for sample in samples]
        right = [wan[sample, condition] for sample in samples]
        print(f"| {condition} | {sum(left)} | {sum(right)} | {left.count(512)} | {right.count(512)} |")


if __name__ == "__main__":
    main()
