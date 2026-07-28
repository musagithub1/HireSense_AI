"""Regression checks for the HireSense presentation layer."""

from __future__ import annotations

import ui_theme


def test_setup_step_requires_both_context_documents() -> None:
    assert ui_theme.setup_active_step(has_resume=False, has_job_description=False) == 2
    assert ui_theme.setup_active_step(has_resume=True, has_job_description=False) == 2
    assert ui_theme.setup_active_step(has_resume=False, has_job_description=True) == 2
    assert ui_theme.setup_active_step(has_resume=True, has_job_description=True) == 4


def test_stepper_uses_direct_html_without_raw_markup_leak(monkeypatch) -> None:
    rendered: list[str] = []

    def capture(body: str, **_kwargs) -> None:
        rendered.append(body)

    def reject_markdown(*_args, **_kwargs) -> None:
        raise AssertionError("The setup stepper must not pass through Markdown")

    monkeypatch.setattr(ui_theme.st, "html", capture)
    monkeypatch.setattr(ui_theme.st, "markdown", reject_markdown)

    ui_theme.render_stepper(2)

    markup = rendered[-1]
    assert markup.count('role="listitem"') == 4
    assert markup.count('aria-current="step"') == 1
    assert '<div class="hs-step active" role="listitem" aria-current="step">' in markup
    assert "\n" not in markup


def test_theme_is_responsive_and_reduced_motion_safe() -> None:
    css = ui_theme.THEME_CSS
    assert "--hs-primary: #7c5cff" in css
    assert "@media (max-width: 640px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@import" not in css


def test_live_header_escapes_dynamic_content(monkeypatch) -> None:
    rendered: list[str] = []

    def capture(body: str, **_kwargs) -> None:
        rendered.append(body)

    monkeypatch.setattr(ui_theme.st, "markdown", capture)
    ui_theme.render_live_header(
        interview_type="<script>alert(1)</script>",
        company="A & B",
        language="English",
        mode="Live voice",
        question_number=2,
        total_questions=5,
    )

    markup = rendered[-1]
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert "A &amp; B" in markup
    assert "Question 2 of 5" in markup


def test_missing_assessment_never_gets_placeholder_score(monkeypatch) -> None:
    rendered: list[str] = []

    def capture(body: str, **_kwargs) -> None:
        rendered.append(body)

    monkeypatch.setattr(ui_theme.st, "markdown", capture)
    ui_theme.render_results_header(
        interview_type="Technical",
        company="General",
        score=None,
        reliability="Not assessed",
    )

    markup = rendered[-1]
    assert "N/A" in markup
    assert "Not assessed" in markup
    assert "50%" not in markup
