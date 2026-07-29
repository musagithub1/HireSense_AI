"""Regression checks for the focused Live Voice Interview product."""

from __future__ import annotations

import inspect

import app
import ui_theme


def test_public_setup_has_one_live_voice_path() -> None:
    source = inspect.getsource(app.render_interview_setup)

    assert "Start live voice interview" in source
    assert "Choose the interview focus" not in source
    assert "Text Interview" not in source
    assert "company_selector" not in source
    assert "num_questions_slider" not in source
    assert "webcam_enabled" not in source
    assert "skill_gap_analysis" not in source


def test_public_main_cannot_route_to_disabled_features() -> None:
    source = inspect.getsource(app.main)

    assert "render_live_voice_session()" in source
    assert "render_active_interview()" not in source
    assert "render_question_bank()" not in source
    assert "render_skill_analysis_page()" not in source
    assert "render_copilot_page()" not in source
    assert "render_coding_page()" not in source


def test_live_voice_defaults_override_stale_workspace_state(monkeypatch) -> None:
    session_state = {
        "page": "coding",
        "interview_mode": "📝 Text Interview",
        "interview_type": "Technical",
        "selected_company": "google",
        "total_questions": 10,
        "webcam_enabled": True,
        "video_recording_enabled": True,
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    app._enforce_live_voice_product_defaults()

    assert session_state["page"] == "interview"
    assert session_state["interview_mode"] == app.LIVE_VOICE_MODE
    assert session_state["interview_type"] == "Mixed"
    assert session_state["selected_company"] == "general"
    assert session_state["total_questions"] == 5
    assert session_state["followup_enabled"] is True
    assert session_state["webcam_enabled"] is False
    assert session_state["video_recording_enabled"] is False


def test_voice_only_header_escapes_language(monkeypatch) -> None:
    rendered: list[str] = []

    def capture(body: str, **_kwargs) -> None:
        rendered.append(body)

    monkeypatch.setattr(ui_theme.st, "markdown", capture)
    ui_theme.render_voice_only_header(
        language="<script>alert(1)</script>",
        question_number=2,
        total_questions=5,
    )

    markup = rendered[-1]
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "Question 2 of 5" in markup
    assert "Live voice interview" in markup
