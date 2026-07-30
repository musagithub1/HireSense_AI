"""Validation tests for untrusted browser component data."""

from __future__ import annotations

import webcam_component
from voice_input_component import _normalize_result


def test_webcam_never_substitutes_invalid_scores() -> None:
    for value in (None, {}, {"status": "ready", "stress_score": "not-a-number"}):
        reading = webcam_component.normalize_emotion_reading(value)
        assert reading["stress_score"] is None
        assert reading["confident_score"] is None
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
    assert abs(reading["confident_score"] - 0.22) < 1e-12
    assert abs(reading["calm_score"] - 0.22) < 1e-12
    assert reading["state"] == "stressed_like"
    assert webcam_component.reading_is_usable(reading)


def test_facial_support_requires_repeated_high_quality_checkpoints() -> None:
    one_reading = [
        {
            "stress_level": 0.82,
            "source": "trained_facial_model",
            "sample_count": 20,
        }
    ]
    assert webcam_component.interviewer_support_state(one_reading) == "neutral"

    repeated = [
        *one_reading,
        {
            "stress_level": 0.76,
            "source": "trained_facial_model",
            "sample_count": 34,
        },
    ]
    assert (
        webcam_component.interviewer_support_state(repeated)
        == "stress_signal"
    )

    low_sample = [
        *one_reading,
        {
            "stress_level": 0.91,
            "source": "trained_facial_model",
            "sample_count": 2,
        },
    ]
    assert webcam_component.interviewer_support_state(low_sample) == "neutral"


def test_facial_summary_reports_expression_checkpoints_not_confidence() -> None:
    summary = webcam_component.summarize_facial_expression_timeline(
        [
            {
                "stress_level": 0.18,
                "source": "trained_facial_model",
                "sample_count": 15,
            },
            {
                "stress_level": 0.35,
                "source": "trained_facial_model",
                "sample_count": 28,
            },
            {
                "stress_level": 0.52,
                "source": "trained_facial_model",
                "sample_count": 41,
            },
            {
                "stress_level": 0.92,
                "source": "developer_override",
                "sample_count": 1,
            },
        ]
    )

    assert summary is not None
    assert summary["checkpoint_count"] == 3
    assert summary["confident_like_count"] == 2
    assert summary["uncertain_count"] == 1
    assert summary["stressed_like_count"] == 0
    assert summary["label"] == "Mostly confident-like expressions"
    assert "internal confidence" in summary["disclaimer"]


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


def test_voice_result_accepts_only_bounded_delivery_telemetry() -> None:
    result = _normalize_result(
        {
            "action": "answer",
            "answer": "I built and measured the result.",
            "submission_id": "delivery-1",
            "word_count": 7,
            "hesitations": 1,
            "recognition_confidence": 0.8421,
            "response_start_ms": 1250,
            "speaking_duration_ms": 18_500,
            "pause_count": 2,
            "pause_ms": 1_800,
            "manual_submit": False,
        }
    )

    assert result is not None
    assert result["recognition_confidence"] == 0.842
    assert result["response_start_ms"] == 1250
    assert result["speaking_duration_ms"] == 18_500
    assert result["pause_count"] == 2
    assert result["pause_ms"] == 1_800
    assert result["manual_submit"] is False

    invalid = _normalize_result(
        {
            "action": "answer",
            "answer": "Answer",
            "submission_id": "delivery-2",
            "recognition_confidence": 4.2,
            "response_start_ms": -50,
        }
    )
    assert invalid is not None
    assert "recognition_confidence" not in invalid
    assert invalid["response_start_ms"] == 0
