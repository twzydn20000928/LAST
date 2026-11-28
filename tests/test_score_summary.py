import json

import pytest

from last.score_message import score_summary


@pytest.mark.parametrize("legacy", [False, True])
def test_rescore_matches_video_and_retains_incomplete_conditions(tmp_path, legacy):
    prediction = tmp_path / "drop-prediction.json"
    prediction.write_text(json.dumps({
        "message_hex": "80" + "00" * 63, "frames": 35, "video_sha256": "video-A",
    }))
    row = {"status": "completed", "frames": 35, "received_sha256": "video-A"}
    if not legacy:
        row["prediction"] = prediction.name
    failed = {"status": "failed", "stage": "last.extract", "exit_code": 1}
    summary = {"video_id": "demo", "requested": ["drop", "clip", "blur"],
               "results": {"drop": row, "clip": failed}}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary))
    results = score_summary(path, bytes(64), True)["results"]
    assert results["drop"]["correct_bits"] == 511
    assert results["drop"]["wrong_bit_positions"] == [0]
    assert results["clip"] == failed
    assert results["blur"] == {"status": "pending"}
    row["received_sha256"] = "video-B"
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="does not match"):
        score_summary(path, bytes(64), False)
