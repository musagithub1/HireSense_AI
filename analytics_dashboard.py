"""Honest interview-practice analytics for HireSense AI.

Facial-model readings are optional and never replaced with synthetic values.
They are displayed as an experimental practice signal and are not included in
the interview performance grade.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import streamlit as st


def _valid_readings(stress_timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    readings: list[dict[str, Any]] = []
    for index, entry in enumerate(stress_timeline):
        value = entry.get("stress_level")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        score = float(value)
        if not math.isfinite(score) or not 0 <= score <= 1:
            continue
        readings.append(
            {
                "stress_level": score,
                "timestamp": entry.get("timestamp", index * 5),
                "source": entry.get("source", "unverified"),
            }
        )
    return readings


def calculate_performance_metrics(
    stress_timeline: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    total_questions: int,
    evidence_assessment: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calculate metrics without inventing missing facial-model readings."""
    all_readings = _valid_readings(stress_timeline)
    readings = [
        item
        for item in all_readings
        if item["source"] in {"trained_facial_model", "trained_model"}
    ]
    excluded_readings = len(all_readings) - len(readings)
    stress_values = [item["stress_level"] for item in readings]

    if stress_values:
        average = sum(stress_values) / len(stress_values)
        variance = sum((value - average) ** 2 for value in stress_values) / len(
            stress_values
        )
        recoveries = [
            previous - current
            for previous, current in zip(stress_values, stress_values[1:])
            if current < previous
        ]
        zones = {
            "high": sum(value > 0.7 for value in stress_values)
            / len(stress_values)
            * 100,
            "medium": sum(0.4 <= value <= 0.7 for value in stress_values)
            / len(stress_values)
            * 100,
            "low": sum(value < 0.4 for value in stress_values)
            / len(stress_values)
            * 100,
        }
        composure = {
            "available": True,
            "average_stress": average,
            "peak_stress": max(stress_values),
            "lowest_stress": min(stress_values),
            "stress_variance": variance,
            "composure_score": (1 - average) * 100,
            "stability_score": max(
                0, 100 - (max(stress_values) - min(stress_values)) * 100
            ),
            "recovery_rate": (sum(recoveries) / len(recoveries) if recoveries else 0.0),
            "readings_count": len(stress_values),
            "excluded_readings_count": excluded_readings,
            "stress_zones": zones,
        }
    else:
        composure = {
            "available": False,
            "average_stress": None,
            "peak_stress": None,
            "lowest_stress": None,
            "stress_variance": None,
            "composure_score": None,
            "stability_score": None,
            "recovery_rate": None,
            "readings_count": 0,
            "excluded_readings_count": excluded_readings,
            "stress_zones": {"high": 0.0, "medium": 0.0, "low": 0.0},
        }

    user_responses = []
    for index, item in enumerate(conversation_history):
        if item.get("role") != "user":
            continue
        previous = conversation_history[index - 1] if index else {}
        user_responses.append(
            {
                **item,
                "answered_followup": bool(previous.get("is_followup")),
            }
        )

    answered = [item for item in user_responses if item.get("content") != "[Skipped]"]
    skipped = [item for item in user_responses if item.get("content") == "[Skipped]"]
    base_answered = [item for item in answered if not item["answered_followup"]]
    base_skipped = [item for item in skipped if not item["answered_followup"]]
    followups_answered = [item for item in answered if item["answered_followup"]]
    total_words = sum(len(str(item.get("content", "")).split()) for item in answered)
    average_length = total_words / len(answered) if answered else 0.0
    question_count = max(0, int(total_questions))
    engagement = {
        "questions_answered": len(base_answered),
        "questions_skipped": len(base_skipped),
        "followups_answered": len(followups_answered),
        "total_answers": len(answered),
        "completion_rate": (
            min(100.0, len(base_answered) / question_count * 100)
            if question_count
            else 0.0
        ),
        "total_words": total_words,
        "avg_response_length": average_length,
    }

    assessment = (
        evidence_assessment if isinstance(evidence_assessment, dict) else {}
    )
    raw_score_5 = assessment.get("overall_score_5")
    score_5 = (
        float(raw_score_5)
        if isinstance(raw_score_5, (int, float))
        and not isinstance(raw_score_5, bool)
        and 1 <= float(raw_score_5) <= 5
        and assessment.get("available") is True
        else None
    )
    score_100 = round(score_5 / 5 * 100, 1) if score_5 is not None else None
    performance = {
        "available": score_5 is not None,
        "overall_score": score_100,
        "evidence_score_5": score_5,
        "reliability": assessment.get("overall_reliability", "Unavailable"),
        "coverage_percent": assessment.get("coverage_percent", 0.0),
        "available_dimensions": assessment.get("available_dimensions", 0),
        "total_dimensions": assessment.get("total_dimensions", 7),
        "composure_component": None,
        "weights": {
            "facial_signal": 0.0,
            "response_length": 0.0,
            "evidence_rubric": 1.0 if score_5 is not None else 0.0,
        },
    }

    timeline = {
        "timestamps": [item["timestamp"] for item in readings],
        "stress_levels": stress_values,
        "calm_signal_levels": [1 - value for value in stress_values],
        "sources": [item["source"] for item in readings],
    }
    return {
        "composure": composure,
        "engagement": engagement,
        "performance": performance,
        "evidence_assessment": assessment,
        "timeline": timeline,
    }


def get_grade(score: float) -> str:
    """Convert a numerical practice score to a letter grade."""
    thresholds = [
        (90, "A+"),
        (85, "A"),
        (80, "A-"),
        (75, "B+"),
        (70, "B"),
        (65, "B-"),
        (60, "C+"),
        (55, "C"),
        (50, "C-"),
        (45, "D"),
    ]
    return next((grade for threshold, grade in thresholds if score >= threshold), "F")


def render_metrics_cards(metrics: dict[str, Any]) -> None:
    """Render the main dashboard cards."""
    columns = st.columns(4)
    performance = metrics["performance"]
    engagement = metrics["engagement"]
    columns[0].metric(
        "Evidence Score",
        (
            f"{performance['evidence_score_5']:.2f}/5"
            if performance["available"]
            else "Not assessed"
        ),
        delta=f"Reliability: {performance['reliability']}",
    )
    columns[1].metric(
        "Scoring Coverage",
        (
            f"{performance['available_dimensions']}/"
            f"{performance['total_dimensions']}"
        ),
        delta=f"{performance['coverage_percent']:.0f}% of rubric",
    )
    columns[2].metric(
        "Completion Rate",
        f"{engagement['completion_rate']:.0f}%",
        delta=f"{engagement['questions_answered']} answered",
    )
    columns[3].metric(
        "Transcript Evidence",
        f"{engagement['total_answers']} answers",
        delta=f"{engagement['total_words']} candidate words",
    )


def render_stress_timeline_chart(metrics: dict[str, Any]) -> None:
    """Render the optional facial-signal timeline."""
    st.markdown("### Facial signal timeline")
    timeline = metrics["timeline"]
    if not timeline["timestamps"]:
        st.info(
            "No valid facial-model readings were recorded. No replacement "
            "values were added."
        )
        return

    frame = pd.DataFrame(
        {
            "Time": timeline["timestamps"],
            "Estimated stress %": [score * 100 for score in timeline["stress_levels"]],
            "Calm signal %": [score * 100 for score in timeline["calm_signal_levels"]],
        }
    )
    st.line_chart(frame.set_index("Time"), width="stretch")
    peak_index = timeline["stress_levels"].index(max(timeline["stress_levels"]))
    calm_index = timeline["stress_levels"].index(min(timeline["stress_levels"]))
    col1, col2, col3 = st.columns(3)
    col1.info(f"**{len(timeline['timestamps'])}** valid readings")
    col2.warning(f"Peak signal at **{timeline['timestamps'][peak_index]}**")
    col3.success(f"Calmest signal at **{timeline['timestamps'][calm_index]}**")


def render_stress_distribution(metrics: dict[str, Any]) -> None:
    """Render the optional facial-signal distribution."""
    st.markdown("### Facial signal distribution")
    facial = metrics["composure"]
    if not facial["available"]:
        st.info("Distribution unavailable because no valid reading was recorded.")
        return

    zones = facial["stress_zones"]
    labels = [
        ("🟢 Low", "low"),
        ("🟡 Medium", "medium"),
        ("🔴 High", "high"),
    ]
    for column, (label, key) in zip(st.columns(3), labels):
        column.markdown(f"#### {label} stress signal")
        column.markdown(f"### {zones[key]:.1f}%")
        column.progress(zones[key] / 100)


def render_performance_breakdown(metrics: dict[str, Any]) -> None:
    """Render validated rubric scores beside factual answer activity."""
    st.markdown("### Evidence scoring")
    assessment = metrics["evidence_assessment"]
    engagement = metrics["engagement"]
    col1, col2 = st.columns(2)

    col1.markdown("#### Competency rubric")
    dimensions = assessment.get("dimensions", {})
    if metrics["performance"]["available"] and dimensions:
        rows = [
            (
                dimension.get("label", key.replace("_", " ").title()),
                (
                    f"{dimension['score']:.1f}/5"
                    if isinstance(dimension.get("score"), (int, float))
                    else "Insufficient evidence"
                ),
                dimension.get("reliability", "Unavailable"),
            )
            for key, dimension in dimensions.items()
        ]
        col1.dataframe(
            pd.DataFrame(rows, columns=["Dimension", "Score", "Reliability"]),
            hide_index=True,
            width="stretch",
        )
    else:
        col1.info(
            "Generate the evidence assessment to score transcript-supported "
            "competencies. No placeholder score is shown."
        )

    engagement_rows = [
        ("Questions answered", str(engagement["questions_answered"])),
        ("Questions skipped", str(engagement["questions_skipped"])),
        ("Follow-ups answered", str(engagement["followups_answered"])),
        ("Completion rate", f"{engagement['completion_rate']:.0f}%"),
        ("Total words", str(engagement["total_words"])),
        ("Average response", f"{engagement['avg_response_length']:.0f} words"),
    ]
    col2.markdown("#### Answer activity")
    col2.dataframe(
        pd.DataFrame(engagement_rows, columns=["Metric", "Value"]),
        hide_index=True,
        width="stretch",
    )


def render_recommendations(metrics: dict[str, Any]) -> None:
    """Render recommendations based only on available evidence."""
    st.markdown("### 💡 Practice Recommendations")
    recommendations: list[tuple[str, str]] = []
    engagement = metrics["engagement"]
    assessment = metrics["evidence_assessment"]

    for improvement in assessment.get("improvements", [])[:5]:
        recommendations.append(
            (
                "Evidence-based priority",
                str(improvement),
            )
        )
    if engagement["avg_response_length"] < 30:
        recommendations.append(
            (
                "Response depth",
                "Use the STAR structure to add context, action, and a concrete result.",
            )
        )
    if engagement["questions_skipped"]:
        recommendations.append(
            (
                "Question coverage",
                f"You skipped {engagement['questions_skipped']} question(s). "
                "A brief structured attempt is often better practice than skipping.",
            )
        )
    if engagement["completion_rate"] < 100:
        recommendations.append(
            (
                "Completion",
                "Practice concise answers so you can complete the full question set.",
            )
        )
    if engagement["avg_response_length"] > 50:
        st.success("Your responses showed useful detail and depth.")

    if not recommendations and engagement["questions_answered"]:
        st.success("No specific answer-activity issue was identified.")
    elif not recommendations:
        st.info("Answer at least one question to receive recommendations.")
    for area, tip in recommendations:
        st.info(f"**{area}:** {tip}")


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


def _score(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}/100"


def export_analytics_report(
    metrics: dict[str, Any],
    conversation_history: list[dict[str, str]],
    report_text: Optional[str] = None,
) -> str:
    """Generate a Markdown report that preserves unavailable values."""
    del conversation_history
    performance = metrics["performance"]
    engagement = metrics["engagement"]
    assessment = metrics["evidence_assessment"]
    score_text = (
        f"{performance['evidence_score_5']:.2f}/5"
        if performance["available"]
        else "Not assessed"
    )
    dimension_rows = []
    evidence_sections = []
    for key, dimension in assessment.get("dimensions", {}).items():
        score = dimension.get("score")
        dimension_rows.append(
            f"| {dimension.get('label', key)} | "
            f"{f'{score:.1f}/5' if isinstance(score, (int, float)) else 'Insufficient evidence'} | "
            f"{dimension.get('reliability', 'Unavailable')} |"
        )
        excerpts = dimension.get("evidence", [])
        if excerpts:
            evidence_sections.append(
                f"### {dimension.get('label', key)}\n\n"
                + "\n".join(
                    f'- Answer {item["answer_index"]}: "{item["excerpt"]}"'
                    for item in excerpts
                )
                + f"\n\nReason: {dimension.get('reason', '')}"
            )

    report = f"""# HireSense AI Interview Practice Report

Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}

## Summary

| Metric | Value |
|---|---:|
| Evidence score | {score_text} |
| Reliability | {performance["reliability"]} |
| Scoring coverage | {performance["available_dimensions"]}/{performance["total_dimensions"]} dimensions |
| Completion rate | {engagement["completion_rate"]:.0f}% |

## Answer activity

- Questions answered: {engagement["questions_answered"]}
- Questions skipped: {engagement["questions_skipped"]}
- Follow-ups answered: {engagement["followups_answered"]}
- Total words: {engagement["total_words"]}
- Average response length: {engagement["avg_response_length"]:.0f} words

## Evidence rubric

| Dimension | Score | Reliability |
|---|---:|---|
{chr(10).join(dimension_rows) if dimension_rows else "| Assessment | Insufficient evidence | Unavailable |"}

## Verified excerpts

{chr(10).join(evidence_sections) if evidence_sections else "No verified scoring excerpts are available."}

## Scoring method

Scores are accepted only when supported by an excerpt verified against a
candidate answer. Response length, facial appearance, and vocal confidence have
zero scoring weight. Missing evidence remains unavailable.
"""
    if report_text:
        report += f"\n## AI-generated answer feedback\n\n{report_text}\n"
    report += (
        "\n## Important limitation\n\n"
        "This assessment supports structured human review. It does not infer "
        "personality, emotion, truthfulness, disability, or protected traits.\n\n"
        "---\n\n*Generated by HireSense AI.*\n"
    )
    return report


def render_full_dashboard(
    stress_timeline: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    total_questions: int,
    report_text: Optional[str] = None,
    evidence_assessment: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Render the complete analytics dashboard."""
    metrics = calculate_performance_metrics(
        stress_timeline,
        conversation_history,
        total_questions,
        evidence_assessment,
    )
    render_metrics_cards(metrics)
    st.markdown("---")
    render_performance_breakdown(metrics)
    st.markdown("---")
    render_recommendations(metrics)
    st.markdown("---")

    facial = metrics["composure"]
    if facial["available"] or facial["excluded_readings_count"]:
        with st.expander("Optional practice-only facial signal", expanded=False):
            st.caption(
                "Experimental, excluded from evidence scoring, and not suitable "
                "for hiring decisions."
            )
            render_stress_timeline_chart(metrics)
            render_stress_distribution(metrics)
        st.markdown("---")

    st.markdown("### 📥 Export Analytics")
    col1, col2 = st.columns(2)
    report = export_analytics_report(metrics, conversation_history, report_text)
    col1.download_button(
        "📄 Download report",
        report,
        file_name=f"hiresense_report_{datetime.now():%Y%m%d_%H%M%S}.md",
        mime="text/markdown",
        width="stretch",
    )
    raw_data = {
        "metrics": metrics,
        "stress_timeline": _valid_readings(stress_timeline),
        "generated_at": datetime.now().isoformat(),
    }
    col2.download_button(
        "Download raw data",
        json.dumps(raw_data, indent=2),
        file_name=f"hiresense_data_{datetime.now():%Y%m%d_%H%M%S}.json",
        mime="application/json",
        width="stretch",
    )
    return metrics
