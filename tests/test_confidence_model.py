"""Tests for explainable interview-delivery confidence estimates."""

from __future__ import annotations

import confidence_model

STRONG_ANSWER = (
    "During a customer migration project, I designed and implemented a staged "
    "rollout because the old process created a serious operational risk. I led "
    "the testing plan, measured failures after each release, and reduced failed "
    "deployments by 30 percent in one month."
)


def test_concrete_steady_answer_scores_above_short_hesitant_answer() -> None:
    strong = confidence_model.estimate_delivery_confidence(
        STRONG_ANSWER,
        {
            "word_count": 47,
            "hesitations": 1,
            "speaking_duration_ms": 28_000,
            "response_start_ms": 1_600,
            "pause_count": 2,
            "pause_ms": 1_900,
            "recognition_confidence": 0.88,
        },
    )
    developing = confidence_model.estimate_delivery_confidence(
        "Um, like, we basically fixed it somehow.",
        {
            "word_count": 7,
            "hesitations": 3,
            "speaking_duration_ms": 18_000,
            "response_start_ms": 12_000,
            "pause_count": 5,
            "pause_ms": 8_000,
            "recognition_confidence": 0.88,
        },
    )

    assert strong["score"] >= 75
    assert developing["score"] < 50
    assert strong["score"] % 5 == 0
    assert strong["label"] == "Strong delivery"
    assert "hiring recommendation" in strong["disclaimer"]


def test_speech_recognition_certainty_does_not_change_candidate_score() -> None:
    base = {
        "word_count": 47,
        "hesitations": 1,
        "speaking_duration_ms": 28_000,
        "response_start_ms": 1_600,
        "pause_count": 2,
        "pause_ms": 1_900,
    }
    low_recognition = confidence_model.estimate_delivery_confidence(
        STRONG_ANSWER,
        {**base, "recognition_confidence": 0.25},
    )
    high_recognition = confidence_model.estimate_delivery_confidence(
        STRONG_ANSWER,
        {**base, "recognition_confidence": 0.98},
    )

    assert low_recognition["score"] == high_recognition["score"]
    assert (
        low_recognition["features"]["recognition_confidence"]
        != high_recognition["features"]["recognition_confidence"]
    )


def test_interview_summary_uses_rounded_median_and_transcript_entries() -> None:
    history = [
        {
            "role": "user",
            "speech_stats": {
                "delivery_confidence": {
                    "score": 55,
                    "reliability": "Medium",
                    "strengths": ["Clear speaking pace"],
                    "opportunities": ["Add concrete results"],
                }
            },
        },
        {
            "role": "assistant",
            "content": "Next question",
        },
        {
            "role": "user",
            "speech_stats": {
                "delivery_confidence": {
                    "score": 80,
                    "reliability": "High",
                    "strengths": ["Clear speaking pace"],
                    "opportunities": ["Reduce filler words"],
                }
            },
        },
    ]

    summary = confidence_model.summarize_interview_delivery(history)

    assert summary is not None
    assert summary["score"] == 70
    assert summary["answers_analyzed"] == 2
    assert summary["strengths"][0] == "Clear speaking pace"


def test_typed_fallback_does_not_claim_speaking_confidence() -> None:
    signal = confidence_model.estimate_delivery_confidence(
        "I typed this answer because speech recognition was unavailable.",
        {
            "word_count": 9,
            "hesitations": 0,
            "manual_submit": True,
        },
    )

    assert signal["available"] is False
    assert signal["score"] is None
    assert signal["reliability"] == "Unavailable"
