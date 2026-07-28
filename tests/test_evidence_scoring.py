"""Tests for transcript-verified competency scoring."""

from __future__ import annotations

import evidence_scoring


def _history() -> list[dict]:
    return [
        {"role": "assistant", "content": "Tell me about a measurable result."},
        {
            "role": "user",
            "content": (
                "I redesigned the support workflow and reduced response time "
                "from two days to four hours."
            ),
            "timestamp": 12.5,
        },
        {"role": "assistant", "content": "How did you decide what to change?"},
        {
            "role": "user",
            "content": (
                "I compared three options, chose the lowest-risk change because "
                "it preserved customer data, and measured the result for a month."
            ),
            "timestamp": 28.0,
        },
    ]


def test_missing_assessment_never_creates_neutral_scores() -> None:
    result = evidence_scoring.validate_assessment(None, _history())

    assert result["available"] is False
    assert result["overall_score_5"] is None
    assert all(
        dimension["score"] is None
        for dimension in result["dimensions"].values()
    )


def test_unverified_quote_is_rejected_with_its_score() -> None:
    payload = {
        "dimensions": {
            "relevance": {
                "score": 5,
                "reason": "Strong result.",
                "evidence": [
                    {
                        "answer_index": 1,
                        "excerpt": "I increased revenue by one million dollars",
                    }
                ],
            }
        }
    }
    result = evidence_scoring.validate_assessment(payload, _history())

    assert result["available"] is False
    assert result["dimensions"]["relevance"]["score"] is None
    assert result["dimensions"]["relevance"]["evidence"] == []


def test_verified_excerpt_supports_score_and_reliability() -> None:
    payload = {
        "summary": "The candidate gave measurable and reasoned examples.",
        "strengths": ["Quantified operational impact."],
        "improvements": ["Explain stakeholder alignment."],
        "dimensions": {
            key: {
                "score": 4,
                "reason": "Supported by a concrete answer.",
                "evidence": [
                    {
                        "answer_index": 1,
                        "excerpt": (
                            "reduced response time from two days to four hours"
                        ),
                    }
                ],
            }
            for key in evidence_scoring.RUBRIC
        },
    }
    result = evidence_scoring.validate_assessment(
        payload,
        _history(),
        model_name="test-model",
    )

    assert result["available"] is True
    assert result["overall_score_5"] == 4.0
    assert result["overall_score_100"] == 80.0
    assert result["available_dimensions"] == 7
    assert result["dimensions"]["relevance"]["reliability"] == "Medium"
    assert result["dimensions"]["relevance"]["evidence"][0]["timestamp"] == 12.5


def test_report_marks_unavailable_dimensions() -> None:
    payload = {
        "summary": "One supported dimension.",
        "dimensions": {
            "evidence_of_results": {
                "score": 4,
                "reason": "A measured outcome was stated.",
                "evidence": [
                    {
                        "answer_index": 1,
                        "excerpt": (
                            "reduced response time from two days to four hours"
                        ),
                    }
                ],
            }
        },
    }
    result = evidence_scoring.validate_assessment(payload, _history())
    report = evidence_scoring.format_assessment_markdown(result)

    assert "4.00/5" in report
    assert "Facial appearance and" in report
    assert result["dimensions"]["relevance"]["score"] is None
