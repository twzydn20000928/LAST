"""Print the supplement's clean extraction length table from reader timing receipts."""
import argparse
import json
import math
from pathlib import Path
from statistics import median


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs=3, type=Path)
    args = parser.parse_args()
    results = {}
    settings = []
    for path in args.receipts:
        row = json.loads(path.read_bytes())
        frames = row["length_study_frames"]
        times = row["seconds"]
        if (row["status"] != "completed" or row["protocol"] != "supplement"
                or row["method"] != "last" or frames != row["frames"]
                or frames not in (65, 129, 257) or frames in results):
            parser.error(f"{path}: expected a distinct completed LAST length measurement")
        if (row["warmups"] != 2 or row["repeats"] != 5 or len(times) != 5
                or any(not math.isfinite(t) or t <= 0 for t in times)
                or row["peak_allocated_bytes"] <= 0):
            parser.error(f"{path}: invalid timing repetitions or peak memory")
        settings.append([row[k] for k in ("family", "mode", "gpu", "torch_version",
                                          "cuda_version", "source_sha256")])
        results[frames] = median(times), row["peak_allocated_bytes"] / 2**30
    if any(setting != settings[0] for setting in settings):
        parser.error("Use receipts with matching model family, mode, GPU, runtime and source")
    print("| Frames | Median clean extraction (s) | Peak allocated (GiB) |")
    print("| ---: | ---: | ---: |")
    for frames, (seconds, gib) in sorted(results.items()):
        print(f"| {frames} | {seconds:.2f} | {gib:.2f} |")


if __name__ == "__main__":
    main()
