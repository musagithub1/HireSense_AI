"""Regression tests for fast and reliable interview-question delivery."""

from __future__ import annotations

from pathlib import Path

import followup_questions
import hiresense_agent
import interview_arena
import live_voice_interview


def _question_text(events: list[dict]) -> str:
    return "".join(
        event["content"]
        for event in events
        if event.get("type") == "question_chunk"
    )


def test_model_question_is_buffered_and_normalized(monkeypatch) -> None:
    class FakeOrchestrator:
        def run_pipeline(self, **_kwargs):
            yield {"type": "trace", "agent": "Content Agent", "content": "ready"}
            yield {"type": "question_chunk", "content": "Tell me about "}
            yield {
                "type": "question_chunk",
                "content": [{"type": "text", "text": "a difficult project?"}],
            }

    monkeypatch.setattr(
        hiresense_agent, "get_orchestrator", lambda **_kwargs: FakeOrchestrator()
    )

    events = list(
        interview_arena.generate_interview_question(
            "resume and job context",
            [],
            question_number=1,
            interview_type="Mixed",
        )
    )

    assert _question_text(events) == "Tell me about a difficult project?"
    assert any(
        event.get("type") == "question_generation_status"
        and event.get("source") == "model"
        for event in events
    )


def test_failed_model_uses_disclosed_builtin_question(monkeypatch) -> None:
    class BrokenOrchestrator:
        def run_pipeline(self, **_kwargs):
            raise TimeoutError("provider timed out")
            yield

    monkeypatch.setattr(
        hiresense_agent, "get_orchestrator", lambda **_kwargs: BrokenOrchestrator()
    )

    events = list(
        interview_arena.generate_interview_question(
            "resume and job context",
            [],
            question_number=3,
            interview_type="Technical",
        )
    )

    assert _question_text(events).endswith("?")
    assert any(
        event.get("type") == "question_generation_status"
        and event.get("source") == "built_in_fallback"
        and event.get("reason") == "TimeoutError"
        for event in events
    )


def test_first_four_agents_make_no_model_calls(monkeypatch) -> None:
    def fail_if_constructed(*_args, **_kwargs):
        raise AssertionError("A local analysis agent attempted a model call")

    monkeypatch.setattr(hiresense_agent, "ChatOpenRouter", fail_if_constructed)
    context = """
=== CANDIDATE RESUME ===
Senior engineer with 7 years of Python, SQL, Docker, and team leadership.
Master's degree in computer science.
=== JOB DESCRIPTION ===
Python and SQL are required. Kubernetes is preferred for this senior role.
"""
    state = hiresense_agent.create_initial_state(
        context,
        [],
        "neutral",
        1,
        5,
        "Technical",
    )

    for agent_class in (
        hiresense_agent.ContentAgent,
        hiresense_agent.InsightAgent,
        hiresense_agent.ImpactAgent,
        hiresense_agent.StrategyAgent,
    ):
        agent = agent_class("unused-model", 0.2)
        list(agent.run(state))

    assert state["content_analysis"]["candidate_experience_years"] == 7
    assert state["skill_insights"]["matching"] == ["python", "sql"]
    assert state["skill_insights"]["missing"] == ["kubernetes"]
    assert state["interview_strategy"]["focus_area"].startswith(
        "Welcome the candidate as Maya"
    )
    assert state["interview_strategy"]["difficulty"] == "easy"


def test_full_five_agent_pipeline_uses_one_network_model(monkeypatch) -> None:
    calls = {"constructed": 0, "streamed": 0}

    class FakeQuestionModel:
        def __init__(self, **_kwargs):
            calls["constructed"] += 1

        def stream(self, _messages):
            calls["streamed"] += 1
            yield type("Chunk", (), {"content": "What did you build with Python?"})()

    monkeypatch.setattr(hiresense_agent, "ChatOpenRouter", FakeQuestionModel)
    orchestrator = hiresense_agent.HireSenseOrchestrator(
        "fast-question-model", 0.5
    )
    events = list(
        orchestrator.run_pipeline(
            rag_context="""
=== CANDIDATE RESUME ===
Python developer with 5 years of experience.
=== JOB DESCRIPTION ===
Python is required for this backend role.
""",
            conversation_history=[],
            emotional_state="neutral",
            question_number=1,
            total_questions=5,
            interview_type="Technical",
        )
    )

    assert calls == {"constructed": 1, "streamed": 1}
    assert any(event.get("type") == "question_chunk" for event in events)


def test_builtin_bank_covers_full_session() -> None:
    for interview_type in interview_arena.BUILT_IN_QUESTION_BANK:
        questions = [
            interview_arena.get_builtin_interview_question(interview_type, number)
            for number in range(1, 9)
        ]
        assert len(set(questions)) == 8
        assert all(question.endswith("?") for question in questions)


def test_followup_generation_skips_separate_analysis_call(monkeypatch) -> None:
    def fail_if_analyzed(*_args, **_kwargs):
        raise AssertionError("Follow-up flow made an unnecessary analysis call")

    def fake_followup(**_kwargs):
        yield "What measurable result came from that work?"

    monkeypatch.setattr(
        followup_questions, "analyze_answer_for_followup", fail_if_analyzed
    )
    monkeypatch.setattr(
        followup_questions, "generate_followup_question", fake_followup
    )

    events = list(
        followup_questions.generate_smart_followup(
            original_question="Tell me about the project?",
            candidate_answer=(
                "I led the implementation and reduced processing time by "
                "thirty percent after measuring the bottleneck."
            ),
        )
    )

    assert events[-1] == "What measurable result came from that work?"
    assert any(
        isinstance(event, dict)
        and event.get("type") == "question_generation_status"
        and event.get("source") == "model"
        for event in events
    )


def test_followup_targets_missing_evidence_without_randomness() -> None:
    clarification = followup_questions.should_ask_followup(
        answer="We fixed it quickly.",
        question="Tell me about a difficult incident.",
        question_number=1,
        total_questions=5,
        time_elapsed_seconds=20,
        max_followups_per_question=1,
        current_followups=0,
        interview_type="Behavioral",
    )
    assert clarification["suggested_type"] == "clarification"

    ownership = followup_questions.should_ask_followup(
        answer=(
            "During a client project, the team redesigned the onboarding flow "
            "and customer completion improved by 25 percent over the next month."
        ),
        question="Tell me about a project.",
        question_number=2,
        total_questions=5,
        time_elapsed_seconds=90,
        max_followups_per_question=1,
        current_followups=0,
        interview_type="Behavioral",
    )
    assert ownership["suggested_type"] == "ownership"

    impact = followup_questions.should_ask_followup(
        answer=(
            "During a customer migration project, I designed and implemented a "
            "staged rollout because the old system had a high operational risk."
        ),
        question="Tell me about a difficult migration.",
        question_number=3,
        total_questions=5,
        time_elapsed_seconds=150,
        max_followups_per_question=1,
        current_followups=0,
        interview_type="Technical",
    )
    assert impact["suggested_type"] == "impact"

    complete = followup_questions.should_ask_followup(
        answer=(
            "During a customer migration project, I designed and implemented a "
            "staged rollout because it reduced operational risk, and the change "
            "cut failed deployments by 30 percent in one month."
        ),
        question="Tell me about a difficult migration.",
        question_number=3,
        total_questions=5,
        time_elapsed_seconds=150,
        max_followups_per_question=1,
        current_followups=0,
        interview_type="Technical",
    )
    assert complete["should_followup"] is False


def test_rephrase_preserves_explicit_unavailable_state(monkeypatch) -> None:
    class FakeModel:
        def __init__(self, **_kwargs):
            pass

        def invoke(self, _messages):
            return type(
                "Response",
                (),
                {"content": "What did you personally do to resolve the incident?"},
            )()

    monkeypatch.setattr(interview_arena, "ChatOpenRouter", FakeModel)
    result = interview_arena.rephrase_interview_question(
        "Could you elucidate your individual remediation contribution?",
        model_name="test-model",
    )
    assert result["source"] == "model_rephrase"
    assert result["question"].endswith("?")


def test_live_voice_component_keeps_stable_browser_session(monkeypatch) -> None:
    calls = []

    def fake_render_voice_input(**kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(
        live_voice_interview, "render_voice_input", fake_render_voice_input
    )
    for number in (1, 2):
        live_voice_interview.render_live_voice_component(
            question_text=f"Question {number}?",
            question_num=number,
            total_questions=5,
        )

    assert [call["key"] for call in calls] == [
        "live_voice_interview",
        "live_voice_interview",
    ]
    assert all(call["tts_enabled"] is True for call in calls)


def test_voice_frontend_requires_user_audio_activation() -> None:
    source = (
        Path(__file__).parents[1]
        / "voice_input"
        / "frontend"
        / "src"
        / "main.js"
    ).read_text()
    markup = (
        Path(__file__).parents[1]
        / "voice_input"
        / "frontend"
        / "index.html"
    ).read_text()

    assert "audioActivated" in source
    assert "Start interview" in source
    assert 'id="play-question"' in markup
    assert 'id="transcript"' in markup
    assert 'id="rephrase-question"' in markup
    assert 'id="response-time"' in markup
    for state in (
        "Listening",
        "Processing",
        "Speaking",
        "Paused",
        "Connection lost",
    ):
        assert state in source
