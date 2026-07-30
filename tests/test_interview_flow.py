"""Tests for the gradual, human-style interview progression."""

from __future__ import annotations

import inspect

import hiresense_agent
import interview_flow


def test_eight_stages_progress_from_basic_to_challenging_to_closing() -> None:
    phases = [
        interview_flow.phase_for_question(number, 8)
        for number in range(1, 9)
    ]

    assert [phase.key for phase in phases] == [
        "introduction",
        "motivation",
        "experience",
        "collaboration",
        "role_depth",
        "problem_solving",
        "advanced_challenge",
        "closing",
    ]
    assert [phase.difficulty for phase in phases] == [
        "easy",
        "easy",
        "medium",
        "medium",
        "medium",
        "hard",
        "hard",
        "reflection",
    ]
    assert phases[0].allow_followup is False
    assert phases[-1].allow_followup is False


def test_fallback_questions_match_the_natural_stage() -> None:
    first = interview_flow.fallback_question(1, 8)
    advanced = interview_flow.fallback_question(7, 8)
    closing = interview_flow.fallback_question(8, 8)

    assert first.startswith("Hi, I am Maya")
    assert "more challenging" in advanced
    assert closing.startswith("Before we finish")
    assert all(value.endswith("?") for value in (first, advanced, closing))


def test_delivery_guidance_never_claims_to_know_emotion() -> None:
    history = [
        {
            "role": "user",
            "speech_stats": {
                "delivery_confidence": {
                    "score": 35,
                    "reliability": "High",
                }
            },
        }
    ]

    guidance = interview_flow.latest_delivery_guidance(history)

    assert "single-part wording" in guidance
    assert "emotion" not in guidance.casefold()
    assert "planned competency and difficulty unchanged" in guidance


def test_facial_support_changes_tone_not_planned_difficulty() -> None:
    source = inspect.getsource(hiresense_agent.StrategyAgent.run)

    assert "Repeated Viva Defense checkpoints were stressed-like" in source
    assert "planned competency and difficulty unchanged" in source
    assert "Use advanced practice questions" not in source
    assert "lower initial difficulty" not in source
