"""Bidirectional webcam component backed by the Viva Defense CNN.

The browser component performs face detection and TensorFlow.js inference
locally. It never substitutes random, brightness-based, or simulated scores
when the model or camera is unavailable.
"""

from __future__ import annotations

import math
from pathlib import Path
from statistics import median
from typing import Any

import streamlit.components.v1 as components

_FRONTEND_BUILD = Path(__file__).parent / "emotion_detector" / "frontend" / "dist"
_MODEL_URL = "app/static/emotion_model/model.json"
_FACE_MODELS_URL = "app/static/face_models/"

MODEL_NAME = "Viva Defense CNN"
MODEL_VERSION = "viva-defense-fer2013-v1"
MODEL_SOURCE_URL = (
    "https://github.com/musagithub1/Viva-Defense-Face-Sensor"
)
MODEL_SOURCE_COMMIT = "f6dfaec3fae94985f66e01963e98d8e4c6db57e2"
MODEL_TEST_ACCURACY = 0.851
MODEL_ROC_AUC = 0.9349
CONFIDENT_LIKE_MAX = 0.40
STRESSED_LIKE_MIN = 0.60
SUPPORT_MODE_MIN_SCORE = 0.70
SUPPORT_MODE_MIN_SAMPLES = 6
SUPPORT_MODE_CONSECUTIVE_CHECKPOINTS = 2

_emotion_detector = components.declare_component(
    "hiresense_emotion_detector",
    path=str(_FRONTEND_BUILD),
)


def _bounded_score(value: Any) -> float | None:
    """Return a finite score in ``[0, 1]`` or ``None``."""
    if isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    return min(1.0, max(0.0, score))


def normalize_emotion_reading(value: Any) -> dict[str, Any]:
    """Validate an untrusted value returned by the browser component."""
    if not isinstance(value, dict):
        return {
            "status": "initializing",
            "stress_score": None,
            "confident_score": None,
            "calm_score": None,
            "state": "unavailable",
            "sample_count": 0,
            "model_loaded": False,
            "message": "Waiting for the trained model.",
            "error_code": None,
        }

    stress_score = _bounded_score(value.get("stress_score"))
    confident_score = None if stress_score is None else 1.0 - stress_score
    status = str(value.get("status", "unavailable"))
    if status not in {"initializing", "ready", "unavailable", "error"}:
        status = "unavailable"

    if status != "ready" or stress_score is None:
        state = "unavailable"
        stress_score = None
        confident_score = None
    elif stress_score < CONFIDENT_LIKE_MAX:
        state = "confident_like"
    elif stress_score > STRESSED_LIKE_MIN:
        state = "stressed_like"
    else:
        state = "uncertain"

    try:
        sample_count = max(0, int(value.get("sample_count", 0)))
    except (TypeError, ValueError):
        sample_count = 0

    return {
        "status": status,
        "stress_score": stress_score,
        "confident_score": confident_score,
        # Retained for compatibility with older saved browser state.
        "calm_score": confident_score,
        "state": state,
        "sample_count": sample_count,
        "model_loaded": bool(value.get("model_loaded", False)),
        "model_name": str(value.get("model_name", MODEL_NAME)),
        "model_version": str(value.get("model_version", MODEL_VERSION)),
        "measured_at": value.get("measured_at"),
        "message": str(value.get("message", "")),
        "error_code": value.get("error_code"),
    }


def render_webcam_emotion_detector(
    *,
    key: str,
    default: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render the detector and return its latest validated browser reading."""
    if not _FRONTEND_BUILD.joinpath("index.html").is_file():
        return normalize_emotion_reading(
            {
                "status": "error",
                "message": "Emotion detector frontend has not been built.",
                "error_code": "FRONTEND_BUILD_MISSING",
            }
        )

    value = _emotion_detector(
        model_url=_MODEL_URL,
        face_models_url=_FACE_MODELS_URL,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        default=default,
        key=key,
    )
    return normalize_emotion_reading(value)


def reading_is_usable(reading: dict[str, Any] | None) -> bool:
    """Return whether a reading came from successful trained-model inference."""
    return bool(
        reading
        and reading.get("status") == "ready"
        and reading.get("model_loaded")
        and _bounded_score(reading.get("stress_score")) is not None
    )


def _valid_timeline_readings(
    timeline: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Return genuine, finite Viva Defense checkpoints only."""
    if not isinstance(timeline, list):
        return []

    valid: list[dict[str, Any]] = []
    for item in timeline:
        if not isinstance(item, dict):
            continue
        if item.get("source") != "trained_facial_model":
            continue
        score = _bounded_score(item.get("stress_level"))
        if score is None:
            continue
        try:
            sample_count = max(0, int(item.get("sample_count", 0)))
        except (TypeError, ValueError):
            sample_count = 0
        valid.append(
            {
                **item,
                "stress_level": score,
                "sample_count": sample_count,
            }
        )
    return valid


def interviewer_support_state(
    timeline: list[dict[str, Any]] | None,
) -> str:
    """Return a restrained tone hint from repeated stressed-like checkpoints.

    The planned competency and difficulty never change. A single facial reading
    is not enough to alter interviewer wording.
    """
    readings = _valid_timeline_readings(timeline)
    required = SUPPORT_MODE_CONSECUTIVE_CHECKPOINTS
    if len(readings) < required:
        return "neutral"

    recent = readings[-required:]
    if all(
        item["stress_level"] >= SUPPORT_MODE_MIN_SCORE
        and item["sample_count"] >= SUPPORT_MODE_MIN_SAMPLES
        for item in recent
    ):
        return "stress_signal"
    return "neutral"


def summarize_facial_expression_timeline(
    timeline: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Summarize question-level expression checkpoints without grading them."""
    readings = _valid_timeline_readings(timeline)
    if not readings:
        return None

    scores = [item["stress_level"] for item in readings]
    confident_like = sum(score < CONFIDENT_LIKE_MAX for score in scores)
    stressed_like = sum(score > STRESSED_LIKE_MIN for score in scores)
    uncertain = len(scores) - confident_like - stressed_like
    median_score = float(median(scores))

    if confident_like > max(stressed_like, uncertain):
        label = "Mostly confident-like expressions"
    elif stressed_like > max(confident_like, uncertain):
        label = "Mostly stressed-like expressions"
    else:
        label = "Mixed or uncertain expressions"

    return {
        "available": True,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "checkpoint_count": len(scores),
        "confident_like_count": confident_like,
        "stressed_like_count": stressed_like,
        "uncertain_count": uncertain,
        "median_stressed_class_output": round(median_score, 3),
        "label": label,
        "disclaimer": (
            "This describes dataset-defined facial-expression patterns only. "
            "It does not measure internal confidence, competence, honesty, "
            "personality, or hiring suitability."
        ),
    }
