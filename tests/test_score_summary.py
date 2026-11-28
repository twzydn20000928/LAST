import json

import pytest

from last.score_message import score_prediction, score_summary


def test_padded_text_splits_utf8_bytes_from_padding():
    expected = "水".encode().ljust(64, b"\x00")
    recovered = bytearray(expected)
    recovered[2] ^= 1
    recovered[-1] = 255
    result = score_prediction(expected, {"message_hex": recovered.hex()}, False, padded_text=True)
    assert result["correct_bits"] == 503
    assert result["padded_text"] == {"body_bits": 24, "correct_body_bits": 23,
                                     "padding_bits": 488, "correct_padding_bits": 480,
                                     "valid_utf8": False}


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
