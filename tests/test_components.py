"""Validation tests for untrusted browser component data."""

from __future__ import annotations

import webcam_component
from voice_input_component import _normalize_result


def test_webcam_never_substitutes_invalid_scores() -> None:
    for value in (None, {}, {"status": "ready", "stress_score": "not-a-number"}):
        reading = webcam_component.normalize_emotion_reading(value)
        assert reading["stress_score"] is None
        assert reading["calm_score"] is None
        assert reading["state"] == "unavailable"


def test_webcam_accepts_only_ready_model_reading() -> None:
    reading = webcam_component.normalize_emotion_reading(
        {
            "status": "ready",
            "stress_score": 0.78,
            "model_loaded": True,
            "sample_count": 11,
        }
    )
    assert reading["stress_score"] == 0.78
    assert abs(reading["calm_score"] - 0.22) < 1e-12
    assert reading["state"] == "stressed"
    assert webcam_component.reading_is_usable(reading)


def test_voice_result_validation() -> None:
    assert _normalize_result(None) is None
    assert _normalize_result({"action": "answer", "answer": ""}) is None
    assert _normalize_result(
        {
            "action": "answer",
            "answer": "  A structured response.  ",
            "submission_id": "abc",
            "word_count": 3,
            "hesitations": 0,
        }
    ) == {
        "action": "answer",
        "answer": "A structured response.",
        "submission_id": "abc",
        "word_count": 3,
        "hesitations": 0,
    }

    rephrase = _normalize_result(
        {
            "action": "rephrase",
            "answer": "",
            "submission_id": "rewrite-1",
        }
    )
    assert rephrase is not None
    assert rephrase["action"] == "rephrase"
    assert rephrase["answer"] == ""
