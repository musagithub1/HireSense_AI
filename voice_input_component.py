"""Bidirectional browser speech input for HireSense AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_DIST_DIR = Path(__file__).parent / "voice_input" / "frontend" / "dist"
_voice_component = components.declare_component(
    "hiresense_voice_input",
    path=str(_DIST_DIR),
)


def _normalize_result(value: Any) -> dict | None:
    """Validate data returned by the browser component."""
    if not isinstance(value, dict):
        return None
    action = value.get("action")
    if action not in {"answer", "end", "rephrase"}:
        return None

    answer = str(value.get("answer", "")).strip()
    if action == "answer" and not answer:
        return None

    submission_id = str(value.get("submission_id", "")).strip()
    if not submission_id:
        return None

    def _nonnegative_int(name: str) -> int:
        try:
            return max(0, int(value.get(name, 0)))
        except (TypeError, ValueError):
            return 0

    normalized = {
        "action": action,
        "answer": answer[:20_000],
        "submission_id": submission_id[:200],
        "word_count": _nonnegative_int("word_count"),
        "hesitations": _nonnegative_int("hesitations"),
    }

    for name in (
        "response_start_ms",
        "speaking_duration_ms",
        "pause_ms",
    ):
        if name not in value:
            continue
        try:
            milliseconds = int(value.get(name))
        except (TypeError, ValueError):
            continue
        normalized[name] = max(0, min(600_000, milliseconds))

    if "pause_count" in value:
        normalized["pause_count"] = min(
            10_000,
            _nonnegative_int("pause_count"),
        )
    if "manual_submit" in value:
        normalized["manual_submit"] = bool(value.get("manual_submit"))

    if "recognition_confidence" in value:
        try:
            recognition_confidence = float(value.get("recognition_confidence"))
        except (TypeError, ValueError):
            recognition_confidence = -1.0
        if (
            not isinstance(value.get("recognition_confidence"), bool)
            and 0 <= recognition_confidence <= 1
        ):
            normalized["recognition_confidence"] = round(
                recognition_confidence,
                3,
            )

    raw_latency = value.get("latency")
    if isinstance(raw_latency, dict):
        latency: dict[str, Any] = {}
        for name in (
            "capture_ms",
            "end_of_speech_ms",
            "transcript_finalize_ms",
            "question_to_listen_ms",
        ):
            try:
                milliseconds = int(raw_latency.get(name))
            except (TypeError, ValueError):
                continue
            latency[name] = max(0, min(600_000, milliseconds))

        response_mode = str(raw_latency.get("response_mode", "")).strip()
        if response_mode in {"adaptive", "fixed", "manual"}:
            latency["response_mode"] = response_mode
        latency["adaptive_vad"] = bool(raw_latency.get("adaptive_vad", False))
        latency["auto_submitted"] = bool(
            raw_latency.get("auto_submitted", False)
        )
        if latency:
            normalized["latency"] = latency

    return normalized


def render_voice_input(
    *,
    key: str,
    language_code: str = "en-US",
    mode: str = "standard",
    question_text: str = "",
    question_num: int = 1,
    total_questions: int = 1,
    question_revision: int = 0,
    question_label: str = "Interview question",
    language_label: str = "",
    tts_speed: float = 1.0,
    tts_enabled: bool = False,
    interviewer_name: str = "Maya",
    allow_interrupt: bool = False,
) -> dict | None:
    """Render speech recognition and return a submitted transcript directly."""
    if mode not in {"standard", "live", "speaker"}:
        raise ValueError("mode must be 'standard', 'live', or 'speaker'")

    value = _voice_component(
        mode=mode,
        language_code=language_code,
        question_text=question_text,
        question_num=max(1, int(question_num)),
        total_questions=max(1, int(total_questions)),
        question_revision=max(0, int(question_revision)),
        question_label=str(question_label)[:120],
        language_label=str(language_label)[:120],
        tts_speed=max(0.5, min(2.0, float(tts_speed))),
        tts_enabled=bool(tts_enabled or mode in {"live", "speaker"}),
        interviewer_name=str(interviewer_name).strip()[:60] or "Maya",
        allow_interrupt=bool(allow_interrupt and mode == "live"),
        default=None,
        key=key,
    )
    return _normalize_result(value)
