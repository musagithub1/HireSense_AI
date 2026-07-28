"""Bidirectional webcam component backed by the trained emotion model.

The browser component performs face detection and TensorFlow.js inference
locally. It never substitutes random, brightness-based, or simulated scores
when the model or camera is unavailable.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_FRONTEND_BUILD = Path(__file__).parent / "emotion_detector" / "frontend" / "dist"
_MODEL_URL = "app/static/emotion_model/model.json"
_FACE_MODELS_URL = "app/static/face_models/"

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
            "calm_score": None,
            "state": "unavailable",
            "sample_count": 0,
            "model_loaded": False,
            "message": "Waiting for the trained model.",
            "error_code": None,
        }

    stress_score = _bounded_score(value.get("stress_score"))
    calm_score = None if stress_score is None else 1.0 - stress_score
    status = str(value.get("status", "unavailable"))
    if status not in {"initializing", "ready", "unavailable", "error"}:
        status = "unavailable"

    if status != "ready" or stress_score is None:
        state = "unavailable"
        stress_score = None
        calm_score = None
    elif stress_score < 0.4:
        state = "calm"
    elif stress_score > 0.6:
        state = "stressed"
    else:
        state = "uncertain"

    try:
        sample_count = max(0, int(value.get("sample_count", 0)))
    except (TypeError, ValueError):
        sample_count = 0

    return {
        "status": status,
        "stress_score": stress_score,
        "calm_score": calm_score,
        "state": state,
        "sample_count": sample_count,
        "model_loaded": bool(value.get("model_loaded", False)),
        "model_name": str(value.get("model_name", "VivaDefense_FaceSensor")),
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
