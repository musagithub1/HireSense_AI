"""Live voice interview wrapper using the bidirectional speech component."""

from __future__ import annotations

from voice_input_component import render_voice_input


def render_live_voice_component(
    question_text: str,
    question_num: int,
    total_questions: int,
    language_code: str = "en-US",
    language_label: str = "",
    tts_speed: float = 1.0,
    question_revision: int = 0,
    question_label: str = "Interview question",
    interviewer_name: str = "Maya",
    allow_interrupt: bool = True,
) -> dict | None:
    """Speak a question, capture an answer, and return it to Streamlit."""
    return render_voice_input(
        # Keep one iframe for the whole interview. This preserves the user's
        # browser audio activation and microphone permission between questions.
        key="live_voice_interview",
        mode="live",
        question_text=question_text,
        question_num=question_num,
        total_questions=total_questions,
        language_code=language_code,
        language_label=language_label,
        tts_speed=tts_speed,
        question_revision=question_revision,
        question_label=question_label,
        tts_enabled=True,
        interviewer_name=interviewer_name,
        allow_interrupt=allow_interrupt,
    )
