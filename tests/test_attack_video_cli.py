import subprocess
import sys

import pytest

pytest.importorskip("cv2")
pytest.importorskip("imageio_ffmpeg")
Image = pytest.importorskip("PIL.Image")

from last.video import export_mp4, load_mp4


def test_drop_writes_35_frames_and_preserves_existing_output(tmp_path):
    source = tmp_path / "input.mp4"
    output = tmp_path / "edited.mp4"
    export_mp4([Image.new("RGB", (512, 512), (i, i, i)) for i in range(65)], source)
    command = [sys.executable, "-m", "last.attack_video", "--video", str(source),
               "--condition", "drop", "--video-id", "cli-check", "--output", str(output)]
    subprocess.run(command, check=True)
    assert len(load_mp4(output)) == 35
    original = output.read_bytes()
    retry = subprocess.run(command, capture_output=True, text=True)
    assert retry.returncode != 0
    assert "Choose a new output file" in retry.stderr
    assert output.read_bytes() == original
