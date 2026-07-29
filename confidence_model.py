"""Explainable speech-delivery confidence signals for interview coaching.

This module does not infer a person's internal emotional state. It estimates
how steady and evidence-rich one recorded answer sounds using observable
transcript and timing features. The estimate is coaching feedback only.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from statistics import median
from typing import Any

MODEL_VERSION = "delivery-confidence-v1"
DISCLAIMER = (
    "Practice estimate based on this transcript and speaking pattern. It is not "
    "an emotion reading, personality judgment, or hiring recommendation."
)

_ACTION_PATTERN = re.compile(
    r"\bi\s+(?:led|built|created|designed|implemented|decided|analysed|"
    r"analyzed|resolved|changed|proposed|owned|managed|tested|measured|"
    r"communicated|prioriti[sz]ed|investigated|delivered|coordinated)\b",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?\b")


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _answer_evidence(answer: str) -> dict[str, bool]:
    text = " ".join(str(answer).split())
    lowered = text.casefold()
    return {
        "context": any(
            term in lowered
            for term in (
                "when ",
                "during ",
                "project",
                "client",
                "customer",
                "team",
                "deadline",
                "situation",
            )
        ),
        "ownership": bool(_ACTION_PATTERN.search(text)),
        "reasoning": any(
            term in lowered
            for term in (
                "because",
                "therefore",
                "so that",
                "tradeoff",
                "trade-off",
                "considered",
                "risk",
                "decided",
            )
        ),
        "result": bool(_NUMBER_PATTERN.search(text))
        or any(
            term in lowered
            for term in (
                "result",
                "outcome",
                "impact",
                "improved",
                "reduced",
                "saved",
                "increased",
                "learned",
            )
        ),
    }


def _pace_component(words_per_minute: float | None) -> float:
    if words_per_minute is None:
        return 0.6
    if 95 <= words_per_minute <= 175:
        return 1.0
    if 75 <= words_per_minute < 95:
        return 0.7 + (words_per_minute - 75) / 20 * 0.3
    if 175 < words_per_minute <= 205:
        return 1.0 - (words_per_minute - 175) / 30 * 0.35
    if 45 <= words_per_minute < 75:
        return 0.35 + (words_per_minute - 45) / 30 * 0.35
    if 205 < words_per_minute <= 250:
        return 0.65 - (words_per_minute - 205) / 45 * 0.4
    return 0.2


def _label(score: int) -> str:
    if score >= 75:
        return "Strong delivery"
    if score >= 50:
        return "Steady delivery"
    return "Developing delivery"


def estimate_delivery_confidence(
    answer: str,
    speech_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate observable answer delivery with bounded, explainable features."""
    stats = speech_stats if isinstance(speech_stats, dict) else {}
    words = str(answer).split()
    word_count = max(len(words), int(_number(stats.get("word_count"), 0)))
    hesitations = max(0, int(_number(stats.get("hesitations"), 0)))
    capture_ms = _number(
        stats.get("speaking_duration_ms") or stats.get("capture_ms"),
        0,
    )
    response_start_ms = _number(stats.get("response_start_ms"), 0)
    pause_count = max(0, int(_number(stats.get("pause_count"), 0)))
    pause_ms = max(0, int(_number(stats.get("pause_ms"), 0)))

    words_per_minute = (
        word_count / (capture_ms / 60_000)
        if capture_ms >= 1_000 and word_count
        else None
    )
    filler_ratio = hesitations / max(1, word_count)
    fluency = _clamp(1 - filler_ratio / 0.10)
    pace = _pace_component(words_per_minute)

    response_start_score = (
        1.0
        if not response_start_ms or response_start_ms <= 8_000
        else _clamp(1 - (response_start_ms - 8_000) / 17_000)
    )
    minutes = max(capture_ms / 60_000, 0.25)
    pauses_per_minute = pause_count / minutes
    pause_score = _clamp(1 - max(0.0, pauses_per_minute - 5.0) / 12.0)
    long_pause_share = pause_ms / capture_ms if capture_ms > 0 else 0.0
    pause_score = min(
        pause_score,
        _clamp(1 - max(0.0, long_pause_share - 0.25) / 0.45),
    )
    composure = response_start_score * 0.4 + pause_score * 0.6

    evidence = _answer_evidence(answer)
    specificity = sum(evidence.values()) / len(evidence)
    if word_count < 12:
        completeness = word_count / 12 * 0.35
    elif word_count < 35:
        completeness = 0.35 + (word_count - 12) / 23 * 0.65
    elif word_count <= 190:
        completeness = 1.0
    else:
        completeness = _clamp(1 - (word_count - 190) / 350, 0.55, 1.0)

    components = {
        "fluency": round(fluency * 100),
        "pace": round(pace * 100),
        "composure": round(composure * 100),
        "specificity": round(specificity * 100),
        "completeness": round(completeness * 100),
    }
    weighted = (
        fluency * 0.22
        + pace * 0.16
        + composure * 0.18
        + specificity * 0.29
        + completeness * 0.15
    )
    score = int(round(_clamp(weighted) * 20) * 5)

    recognition_confidence = _number(stats.get("recognition_confidence"), -1)
    if (
        capture_ms < 1_000
        and response_start_ms <= 0
        and recognition_confidence < 0
    ):
        return {
            "available": False,
            "model_version": MODEL_VERSION,
            "score": None,
            "label": "Speaking delivery unavailable",
            "reliability": "Unavailable",
            "components": {},
            "features": {"word_count": word_count},
            "strengths": [],
            "opportunities": [],
            "disclaimer": DISCLAIMER,
        }
    telemetry_count = sum(
        (
            capture_ms >= 1_000,
            response_start_ms > 0,
            "pause_count" in stats,
            0 <= recognition_confidence <= 1,
        )
    )
    if word_count >= 25 and telemetry_count >= 3:
        reliability = "High"
    elif word_count >= 12 and telemetry_count >= 1:
        reliability = "Medium"
    else:
        reliability = "Low"

    strengths: list[str] = []
    opportunities: list[str] = []
    if fluency >= 0.75:
        strengths.append("Limited filler words")
    else:
        opportunities.append("Reduce filler words and restart phrases")
    if pace >= 0.75:
        strengths.append("Clear speaking pace")
    else:
        opportunities.append("Use a steadier speaking pace")
    if specificity >= 0.75:
        strengths.append("Concrete evidence and ownership")
    else:
        opportunities.append("Add context, personal action, reasoning, and results")
    if completeness >= 0.8:
        strengths.append("Answer developed beyond a short claim")
    else:
        opportunities.append("Develop the answer with one complete example")
    if composure < 0.55:
        opportunities.append("Use a short thinking pause, then answer in a clear structure")

    return {
        "available": True,
        "model_version": MODEL_VERSION,
        "score": score,
        "label": _label(score),
        "reliability": reliability,
        "components": components,
        "features": {
            "word_count": word_count,
            "hesitations": hesitations,
            "words_per_minute": (
                round(words_per_minute) if words_per_minute is not None else None
            ),
            "response_start_ms": (
                round(response_start_ms) if response_start_ms > 0 else None
            ),
            "pause_count": pause_count if "pause_count" in stats else None,
            "recognition_confidence": (
                round(recognition_confidence, 3)
                if 0 <= recognition_confidence <= 1
                else None
            ),
        },
        "strengths": strengths[:3],
        "opportunities": opportunities[:3],
        "disclaimer": DISCLAIMER,
    }


def summarize_interview_delivery(
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Aggregate per-answer delivery signals without creating fake precision."""
    signals: list[dict[str, Any]] = []
    for entry in conversation_history:
        if entry.get("role") != "user":
            continue
        speech_stats = entry.get("speech_stats")
        if not isinstance(speech_stats, dict):
            continue
        signal = speech_stats.get("delivery_confidence")
        if (
            isinstance(signal, dict)
            and signal.get("available", True)
            and isinstance(signal.get("score"), (int, float))
        ):
            signals.append(signal)
    if not signals:
        return None

    score = int(round(median(float(item["score"]) for item in signals) / 5) * 5)
    reliability_values = [str(item.get("reliability", "Low")) for item in signals]
    if reliability_values.count("High") >= max(1, len(signals) // 2):
        reliability = "High"
    elif any(value in {"High", "Medium"} for value in reliability_values):
        reliability = "Medium"
    else:
        reliability = "Low"

    strength_counts = Counter(
        strength
        for item in signals
        for strength in item.get("strengths", [])
        if isinstance(strength, str)
    )
    opportunity_counts = Counter(
        opportunity
        for item in signals
        for opportunity in item.get("opportunities", [])
        if isinstance(opportunity, str)
    )
    return {
        "model_version": MODEL_VERSION,
        "score": score,
        "label": _label(score),
        "reliability": reliability,
        "answers_analyzed": len(signals),
        "strengths": [item for item, _ in strength_counts.most_common(3)],
        "opportunities": [
            item for item, _ in opportunity_counts.most_common(3)
        ],
        "disclaimer": DISCLAIMER,
    }
