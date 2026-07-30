"""Regression checks for the focused Live Voice Interview product."""

from __future__ import annotations

import inspect

import app
import interview_flow
import ui_theme


def test_public_setup_has_one_live_voice_path() -> None:
    source = inspect.getsource(app.render_interview_setup)

    assert "Start live voice interview" in source
    assert "Choose the interview focus" not in source
    assert "Text Interview" not in source
    assert "company_selector" not in source
    assert "num_questions_slider" not in source
    assert "Use my Viva Defense facial-expression model" in source
    assert "facial_signal_consent" in source
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
    assert session_state["total_questions"] == 8
    assert session_state["total_questions"] == len(interview_flow.INTERVIEW_PHASES)
    assert session_state["followup_enabled"] is True
    assert session_state["max_total_followups"] == 3
    assert session_state["webcam_enabled"] is False
    assert session_state["video_recording_enabled"] is False
    assert session_state["save_resume_file"] is True


def test_camera_model_runs_only_after_explicit_consent(monkeypatch) -> None:
    session_state = {
        "facial_signal_consent": True,
        "webcam_enabled": False,
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    app._enforce_live_voice_product_defaults()

    assert session_state["webcam_enabled"] is True


def test_voice_only_header_escapes_language(monkeypatch) -> None:
    rendered: list[str] = []

    def capture(body: str, **_kwargs) -> None:
        rendered.append(body)

    monkeypatch.setattr(ui_theme.st, "markdown", capture)
    ui_theme.render_voice_only_header(
        language="<script>alert(1)</script>",
        question_number=2,
        total_questions=8,
    )

    markup = rendered[-1]
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "Question 2 of 8" not in markup
    assert "Live voice interview" in markup
    assert "3D interviewer" in markup


def test_next_question_is_not_prepared_before_current_answer() -> None:
    session_source = inspect.getsource(app.render_live_voice_session)
    advance_source = inspect.getsource(app._advance_after_answer)
    begin_source = inspect.getsource(app._begin_live_voice_interview)

    assert "_schedule_next_base_question()" not in session_source
    assert "_schedule_next_base_question(" not in advance_source
    assert "_schedule_next_base_question(" not in begin_source
    assert "awaiting_question" in advance_source


def test_starting_interview_saves_resume_text_and_private_pdf(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeDatabaseService:
        def start_interview(self, **kwargs):
            calls.append(("start", kwargs))
            return {
                "application_id": "00000000-0000-0000-0000-000000000003",
                "job_id": "00000000-0000-0000-0000-000000000004",
            }

        def upload_resume(self, **kwargs):
            calls.append(("upload", kwargs))
            return "private/resume.pdf"

    session_state = {
        "selected_company": "general",
        "interview_mode": app.LIVE_VOICE_MODE,
        "target_role": "AI Engineer",
        "interview_jd_text": "Build reliable AI systems.",
        "interview_resume_text": "Python engineer.",
        "selected_language": "en",
        "interview_type": "Mixed",
        "total_questions": 8,
        "_resume_upload_name": "resume.pdf",
        "_resume_upload_bytes": b"%PDF-1.7 resume",
        "_recoverable_interview": None,
    }
    monkeypatch.setattr(app.st, "session_state", session_state)
    monkeypatch.setattr(app, "_database_session_ready", lambda: True)
    monkeypatch.setattr(app, "_database_service", FakeDatabaseService)

    app._start_database_interview(
        "00000000-0000-0000-0000-000000000002"
    )

    assert calls[0][0] == "start"
    assert calls[0][1]["resume_text"] == "Python engineer."
    assert calls[1][0] == "upload"
    assert calls[1][1]["content"] == b"%PDF-1.7 resume"
    assert session_state["resume_saved_to_supabase"] is True
    assert session_state["resume_storage_status"] == (
        "text_and_private_pdf_saved"
    )
