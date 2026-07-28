"""Tests that unavailable facial data is never fabricated."""

from __future__ import annotations

from analytics_dashboard import (
    calculate_performance_metrics,
    export_analytics_report,
)


def test_missing_model_data_stays_unavailable() -> None:
    history = [
        {"role": "assistant", "content": "Tell me about yourself."},
        {"role": "user", "content": "I build reliable data products."},
    ]
    metrics = calculate_performance_metrics([], history, 1)

    assert metrics["composure"]["available"] is False
    assert metrics["composure"]["average_stress"] is None
    assert metrics["composure"]["composure_score"] is None
    assert metrics["composure"]["stress_zones"] == {
        "high": 0.0,
        "medium": 0.0,
        "low": 0.0,
    }
    assert metrics["performance"]["composure_component"] is None
    assert metrics["performance"]["weights"]["facial_signal"] == 0
    assert metrics["performance"]["available"] is False
    assert metrics["performance"]["overall_score"] is None

    report = export_analytics_report(metrics, history)
    assert "Evidence score | Not assessed" in report
    assert "Facial calm signal" not in report
    assert "response length" in report.casefold()


def test_invalid_readings_are_ignored() -> None:
    readings = [
        {"stress_level": None},
        {"stress_level": "0.8"},
        {"stress_level": -1},
        {"stress_level": 2},
        {"stress_level": float("nan")},
        {
            "stress_level": 0.25,
            "timestamp": 4,
            "source": "trained_facial_model",
        },
        {
            "stress_level": 0.75,
            "timestamp": 9,
            "source": "trained_facial_model",
        },
    ]
    metrics = calculate_performance_metrics(readings, [], 3)

    assert metrics["composure"]["readings_count"] == 2
    assert metrics["composure"]["average_stress"] == 0.5
    assert metrics["timeline"]["timestamps"] == [4, 9]


def test_facial_signal_does_not_create_or_change_score() -> None:
    history = [
        {"role": "user", "content": "word " * 50},
    ]
    low = calculate_performance_metrics(
        [{"stress_level": 0.05, "source": "trained_facial_model"}],
        history,
        1,
    )
    high = calculate_performance_metrics(
        [{"stress_level": 0.95, "source": "trained_facial_model"}],
        history,
        1,
    )
    assert low["performance"]["overall_score"] == high["performance"]["overall_score"]
    assert low["performance"]["overall_score"] is None


def test_validated_evidence_assessment_drives_score() -> None:
    history = [
        {"role": "assistant", "content": "What result did you achieve?"},
        {
            "role": "user",
            "content": "I reduced response time from two days to four hours.",
        },
    ]
    assessment = {
        "available": True,
        "overall_score_5": 4.0,
        "overall_reliability": "Medium",
        "coverage_percent": 71.4,
        "available_dimensions": 5,
        "total_dimensions": 7,
        "dimensions": {},
        "improvements": [],
    }
    metrics = calculate_performance_metrics([], history, 1, assessment)

    assert metrics["performance"]["overall_score"] == 80.0
    assert metrics["performance"]["evidence_score_5"] == 4.0
    assert metrics["performance"]["weights"] == {
        "facial_signal": 0.0,
        "response_length": 0.0,
        "evidence_rubric": 1.0,
    }


def test_developer_override_is_excluded_from_facial_metrics() -> None:
    metrics = calculate_performance_metrics(
        [{"stress_level": 0.9, "source": "developer_override"}],
        [],
        1,
    )
    assert metrics["composure"]["available"] is False
    assert metrics["composure"]["excluded_readings_count"] == 1
