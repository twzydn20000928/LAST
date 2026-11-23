"""Measure differences between two decoded, same-case primary reference videos."""
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def compare(left, right):
    videos = [cv2.VideoCapture(str(path)) for path in (left, right)]
    frames = total = squared = different = 0
    maximum = 0
    try:
        if not all(video.isOpened() for video in videos):
            raise ValueError("Could not open both reference videos")
        while True:
            (ok_a, a), (ok_b, b) = [video.read() for video in videos]
            if ok_a != ok_b:
                raise ValueError("Frame counts differ")
            if not ok_a:
                break
            if a.shape != b.shape:
                raise ValueError("Frame shapes differ")
            delta = cv2.absdiff(a, b)
            different += int(np.count_nonzero(delta))
            squared += int(np.sum(np.square(delta, dtype=np.int32), dtype=np.int64))
            maximum = max(maximum, int(delta.max()))
            frames += 1
            total += delta.size
    finally:
        for video in videos:
            video.release()
    if frames != 65:
        raise ValueError(f"Expected 65 decoded frames per primary reference, got {frames}")
    return dict(frames=frames, identical=different == 0, changed_channel_values=different,
                total_channel_values=total, max_abs_difference_8bit=maximum,
                rmse_8bit=math.sqrt(squared / total))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.left, args.right), indent=2))
