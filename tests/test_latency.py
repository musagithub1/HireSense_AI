"""Regression tests for the low-latency live interview path."""

from __future__ import annotations

import time
from concurrent.futures import Future
from pathlib import Path

import hiresense_agent
import latency_optimizer
from voice_input_component import _normalize_result


def test_prefetched_question_is_handed_off_without_a_second_generation() -> None:
    calls = {"count": 0}

    def generator_factory():
        calls["count"] += 1
        yield {
            "type": "question_generation_status",
            "source": "model",
        }
        yield {
            "type": "question_chunk",
            "content": "What result did your implementation achieve?",
        }

    job = latency_optimizer.schedule_question_prefetch(
        target_question=2,
        cache_key="session-question-2",
        generator_factory=generator_factory,
    )
    resolution = latency_optimizer.resolve_question_prefetch(
        job,
        target_question=2,
        cache_key="session-question-2",
        wait_seconds=1,
    )

    assert resolution.state == "hit"
    assert resolution.question is not None
    assert resolution.question.text.endswith("?")
    assert resolution.question.status["delivery"] == "prefetched"
    assert calls["count"] == 1


def test_inflight_prefetch_uses_a_bounded_handoff_wait() -> None:
    unresolved: Future[latency_optimizer.GeneratedQuestion] = Future()
    job = latency_optimizer.QuestionPrefetch(
        target_question=3,
        cache_key="session-question-3",
        started_at=time.perf_counter(),
        future=unresolved,
    )

    started = time.perf_counter()
    resolution = latency_optimizer.resolve_question_prefetch(
        job,
        target_question=3,
        cache_key="session-question-3",
        wait_seconds=0.01,
    )
    elapsed = time.perf_counter() - started

    assert resolution.state == "timeout"
    assert resolution.reason == "prefetch_not_ready"
    assert elapsed < 0.2
    unresolved.cancel()


def test_prefetch_key_changes_with_interview_state() -> None:
    base = {
        "session_id": "session-a",
        "target_question": 2,
        "interview_type": "Technical",
        "company": "general",
        "rag_context": "resume and role",
        "conversation_history": [{"role": "assistant", "content": "Question one?"}],
    }
    first = latency_optimizer.question_cache_key(**base)
    assert first == latency_optimizer.question_cache_key(**base)
    assert first != latency_optimizer.question_cache_key(
        **{**base, "target_question": 3}
    )
    assert first != latency_optimizer.question_cache_key(
        **{
            **base,
            "conversation_history": [
                {"role": "assistant", "content": "A different question?"}
            ],
        }
    )


def test_question_prompt_uses_compact_facts_not_raw_documents(monkeypatch) -> None:
    captured = {"messages": None, "model_kwargs": None}

    class FakeQuestionModel:
        def __init__(self, **kwargs):
            captured["model_kwargs"] = kwargs

        def stream(self, messages):
            captured["messages"] = messages
            yield type(
                "Chunk",
                (),
                {"content": "How did you use Python to improve a system?"},
            )()

    monkeypatch.setattr(hiresense_agent, "ChatOpenRouter", FakeQuestionModel)
    raw_marker = "RAW_DOCUMENT_MARKER_SHOULD_NOT_REACH_THE_MODEL"
    context = f"""
=== CANDIDATE RESUME ===
Python engineer with 5 years of experience. {raw_marker}
=== JOB DESCRIPTION ===
Python and SQL are required for this senior role. {raw_marker}
"""
    orchestrator = hiresense_agent.HireSenseOrchestrator("test-model", 0.5)
    list(
        orchestrator.run_pipeline(
            rag_context=context,
            conversation_history=[],
            emotional_state="neutral",
            question_number=1,
            total_questions=5,
            interview_type="Technical",
        )
    )

    rendered = "\n".join(
        str(getattr(message, "content", "")) for message in captured["messages"]
    )
    assert raw_marker not in rendered
    assert "Candidate skills: python" in rendered
    assert len(rendered) < 3_500
    assert captured["model_kwargs"]["extra_body"] == {
        "reasoning": {"effort": "none", "exclude": True}
    }


def test_voice_latency_values_are_bounded_and_sanitized() -> None:
    result = _normalize_result(
        {
            "action": "answer",
            "answer": "I reduced processing time by thirty percent.",
            "submission_id": "latency-1",
            "word_count": 7,
            "hesitations": 0,
            "latency": {
                "capture_ms": 8_000,
                "end_of_speech_ms": 940,
                "transcript_finalize_ms": 180,
                "question_to_listen_ms": 2_400,
                "response_mode": "adaptive",
                "adaptive_vad": True,
                "auto_submitted": True,
                "unexpected": "ignored",
            },
        }
    )

    assert result is not None
    assert result["latency"] == {
        "capture_ms": 8_000,
        "end_of_speech_ms": 940,
        "transcript_finalize_ms": 180,
        "question_to_listen_ms": 2_400,
        "response_mode": "adaptive",
        "adaptive_vad": True,
        "auto_submitted": True,
    }


def test_voice_frontend_contains_adaptive_vad_and_safety_fallback() -> None:
    root = Path(__file__).parents[1] / "voice_input" / "frontend"
    source = (root / "src" / "main.js").read_text(encoding="utf-8")
    markup = (root / "index.html").read_text(encoding="utf-8")

    assert "getFloatTimeDomainData" in source
    assert "ADAPTIVE_SILENCE_MS = 900" in source
    assert "2200" in source
    assert 'option value="adaptive" selected' in markup
