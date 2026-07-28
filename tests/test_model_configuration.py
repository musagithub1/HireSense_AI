"""Regression tests for provider selection and resilient model output."""

from __future__ import annotations

from pathlib import Path

import config
import followup_questions
import hiresense_agent
import interview_arena
import live_copilot
import model_utils
import skill_gap_analysis
import ui_theme


def test_deepseek_v4_flash_is_the_project_default(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_EVALUATION_MODEL", raising=False)

    assert config.get_openrouter_model() == "deepseek/deepseek-v4-flash"
    assert config.get_openrouter_evaluation_model() == "deepseek/deepseek-v4-flash"


def test_evaluation_model_follows_explicit_primary_override(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_MODEL", "provider/custom-model")
    monkeypatch.delenv("OPENROUTER_EVALUATION_MODEL", raising=False)

    assert config.get_openrouter_model() == "provider/custom-model"
    assert config.get_openrouter_evaluation_model() == "provider/custom-model"


def test_no_legacy_gemini_default_remains() -> None:
    root = Path(__file__).parents[1]
    searchable = (
        list(root.glob("*.py"))
        + [root / ".env.example", root / "README.md"]
        + list((root / "docs").glob("*.md"))
    )

    for path in searchable:
        assert "google/gemini" not in path.read_text(encoding="utf-8")


def test_orchestrator_cache_changes_with_model(monkeypatch) -> None:
    created: list[tuple[str, float]] = []

    class FakeOrchestrator:
        def __init__(self, model_name: str, temperature: float):
            self.model_name = model_name
            self.temperature = temperature
            created.append((model_name, temperature))

    monkeypatch.setattr(hiresense_agent, "HireSenseOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(hiresense_agent, "_orchestrator", None)

    first = hiresense_agent.get_orchestrator("model-a", 0.5)
    same = hiresense_agent.get_orchestrator("model-a", 0.5)
    changed = hiresense_agent.get_orchestrator("model-b", 0.5)

    assert first is same
    assert changed is not first
    assert created == [("model-a", 0.5), ("model-b", 0.5)]


def test_reasoning_markup_and_provider_preamble_are_removed() -> None:
    raw = (
        "<think>Internal reasoning with {braces}.</think>\n"
        "Here is the question:\n"
        "Question: Tell me about a difficult project? Extra commentary."
    )
    assert (
        model_utils.normalize_question(raw)
        == "Tell me about a difficult project?"
    )


def test_copilot_cache_key_changes_with_context_or_model() -> None:
    first = live_copilot.key_points_signature("resume", "role", "model-a")
    assert first == live_copilot.key_points_signature("resume", "role", "model-a")
    assert first != live_copilot.key_points_signature("resume 2", "role", "model-a")
    assert first != live_copilot.key_points_signature("resume", "role", "model-b")


def test_json_decoder_skips_reasoning_and_leading_text() -> None:
    payload = model_utils.extract_json_object(
        '<think>{"ignored": true}</think>\nResult:\n{"dimensions": {"relevance": 4}}'
    )
    assert payload == {"dimensions": {"relevance": 4}}


def test_every_followup_type_has_a_safe_failure_question(monkeypatch) -> None:
    def broken_generator(**_kwargs):
        raise TimeoutError("provider timeout")
        yield

    monkeypatch.setattr(
        followup_questions,
        "generate_followup_question",
        broken_generator,
    )
    for followup_type in followup_questions.FOLLOWUP_TYPES:
        events = list(
            followup_questions.generate_smart_followup(
                original_question="Tell me about a project?",
                candidate_answer="I led a migration and reduced failures.",
                followup_type=followup_type,
                model_name="test-model",
            )
        )
        assert isinstance(events[-1], str)
        assert events[-1].endswith("?")
        assert any(
            isinstance(event, dict)
            and event.get("source") == "built_in_fallback"
            for event in events
        )


def test_skill_analysis_failure_never_becomes_neutral_match(monkeypatch) -> None:
    class BrokenModel:
        def __init__(self, **_kwargs):
            raise ValueError("missing key")

    monkeypatch.setattr(skill_gap_analysis, "ChatOpenRouter", BrokenModel)
    result = skill_gap_analysis.run_full_skill_analysis(
        "Python developer",
        "Python required",
        model_name="test-model",
    )

    assert result["available"] is False
    assert result["summary_stats"]["overall_score"] is None
    assert result["radar_data"]["categories"] == []
    assert "50%" not in result["formatted_report"]


def test_pdf_boundaries_fail_cleanly() -> None:
    for value in (b"", b"x" * (interview_arena.MAX_PDF_BYTES + 1)):
        try:
            interview_arena.extract_pdf_text(value)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid PDF input should be rejected")


def test_supplied_logo_is_packaged_and_embeddable() -> None:
    assert ui_theme.BRAND_LOGO_PATH.is_file()
    assert ui_theme.BRAND_LOGO_PATH.stat().st_size > 10_000
    assert (
        ui_theme.brand_logo_source()
        == "app/static/brand/hiresense-ai-logo.png"
    )
