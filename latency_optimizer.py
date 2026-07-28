"""Low-latency helpers for the HireSense live interview loop.

The browser remains responsible for microphone capture and speech playback.
This module overlaps generation of the next base question with the candidate's
answer time, applies a short bounded hand-off wait, and records timing metadata
without retaining additional candidate content.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Literal

_PREFETCH_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="hiresense-question-prefetch",
)


def _bounded_seconds(name: str, default: float, *, maximum: float) -> float:
    """Read a positive duration from the environment with safe bounds."""
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(maximum, value))


def prefetch_wait_seconds() -> float:
    """Return the maximum foreground wait for an in-flight prefetched question."""
    return _bounded_seconds(
        "HIRESENSE_PREFETCH_WAIT_SECONDS",
        1.25,
        maximum=3.0,
    )


@dataclass(frozen=True)
class GeneratedQuestion:
    """A completed question plus non-sensitive delivery telemetry."""

    text: str
    status: dict[str, Any]
    generation_ms: int


@dataclass(frozen=True)
class QuestionPrefetch:
    """Handle for one background base-question generation request."""

    target_question: int
    cache_key: str
    started_at: float
    future: Future[GeneratedQuestion]


@dataclass(frozen=True)
class PrefetchResolution:
    """Result of attempting to hand an in-flight question to the live UI."""

    state: Literal["hit", "miss", "timeout", "error"]
    question: GeneratedQuestion | None
    wait_ms: int
    reason: str | None = None


def collect_question_stream(
    generator: Iterator[dict[str, Any] | str],
) -> GeneratedQuestion:
    """Collect one validated question stream and retain its disclosed status."""
    started_at = time.perf_counter()
    text_parts: list[str] = []
    status: dict[str, Any] = {}

    for chunk in generator:
        if isinstance(chunk, dict):
            if chunk.get("type") == "question_chunk":
                text_parts.append(str(chunk.get("content", "")))
            elif chunk.get("type") == "question_generation_status":
                status.update(chunk)
        elif isinstance(chunk, str):
            text_parts.append(chunk)

    generation_ms = max(0, round((time.perf_counter() - started_at) * 1000))
    return GeneratedQuestion(
        text="".join(text_parts).strip(),
        status=status,
        generation_ms=generation_ms,
    )


def question_cache_key(
    *,
    session_id: str,
    target_question: int,
    interview_type: str,
    company: str,
    rag_context: str,
    conversation_history: list[dict[str, Any]],
) -> str:
    """Build an opaque key that invalidates stale prefetched questions."""
    recent_history = [
        {
            "role": str(entry.get("role", ""))[:20],
            "content": str(entry.get("content", ""))[:800],
        }
        for entry in conversation_history[-6:]
    ]
    payload = {
        "session_id": str(session_id),
        "target_question": max(1, int(target_question)),
        "interview_type": str(interview_type),
        "company": str(company),
        "context_digest": hashlib.sha256(
            str(rag_context).encode("utf-8")
        ).hexdigest(),
        "history": recent_history,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def schedule_question_prefetch(
    *,
    target_question: int,
    cache_key: str,
    generator_factory: Callable[[], Iterator[dict[str, Any] | str]],
) -> QuestionPrefetch:
    """Begin generating one future base question in a bounded worker pool."""

    def _run() -> GeneratedQuestion:
        return collect_question_stream(generator_factory())

    return QuestionPrefetch(
        target_question=max(1, int(target_question)),
        cache_key=str(cache_key),
        started_at=time.perf_counter(),
        future=_PREFETCH_EXECUTOR.submit(_run),
    )


def resolve_question_prefetch(
    job: QuestionPrefetch | None,
    *,
    target_question: int,
    cache_key: str,
    wait_seconds: float | None = None,
) -> PrefetchResolution:
    """Return a completed prefetch or fail fast without starting a duplicate call."""
    if (
        not isinstance(job, QuestionPrefetch)
        or job.target_question != max(1, int(target_question))
        or job.cache_key != str(cache_key)
    ):
        return PrefetchResolution("miss", None, 0)

    wait_started = time.perf_counter()
    timeout = (
        prefetch_wait_seconds()
        if wait_seconds is None
        else max(0.0, min(3.0, float(wait_seconds)))
    )
    try:
        question = job.future.result(timeout=timeout)
    except TimeoutError:
        wait_ms = max(0, round((time.perf_counter() - wait_started) * 1000))
        return PrefetchResolution(
            "timeout",
            None,
            wait_ms,
            reason="prefetch_not_ready",
        )
    except Exception as exc:
        wait_ms = max(0, round((time.perf_counter() - wait_started) * 1000))
        return PrefetchResolution(
            "error",
            None,
            wait_ms,
            reason=exc.__class__.__name__,
        )

    wait_ms = max(0, round((time.perf_counter() - wait_started) * 1000))
    total_ms = max(0, round((time.perf_counter() - job.started_at) * 1000))
    status = dict(question.status)
    status.update(
        {
            "delivery": "prefetched",
            "generation_ms": question.generation_ms,
            "prefetch_total_ms": total_ms,
            "prefetch_wait_ms": wait_ms,
        }
    )
    return PrefetchResolution(
        "hit",
        GeneratedQuestion(question.text, status, question.generation_ms),
        wait_ms,
    )


def cancel_question_prefetch(job: QuestionPrefetch | None) -> bool:
    """Cancel a queued prefetch when possible and safely ignore running work."""
    if not isinstance(job, QuestionPrefetch):
        return False
    return job.future.cancel()


def foreground_question(
    generator: Iterator[dict[str, Any] | str],
) -> GeneratedQuestion:
    """Collect a foreground question and label its measured delivery path."""
    question = collect_question_stream(generator)
    status = dict(question.status)
    status.update(
        {
            "delivery": "foreground",
            "generation_ms": question.generation_ms,
            "prefetch_wait_ms": 0,
        }
    )
    return GeneratedQuestion(question.text, status, question.generation_ms)


def latency_event(
    *,
    question_number: int,
    is_followup: bool,
    status: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a bounded, content-free timing event for diagnostics."""
    source = status or {}

    def _milliseconds(name: str) -> int | None:
        value = source.get(name)
        if isinstance(value, bool):
            return None
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None
        return max(0, min(120_000, numeric))

    return {
        "question_number": max(1, int(question_number)),
        "is_followup": bool(is_followup),
        "source": str(source.get("source", "unknown"))[:40],
        "delivery": str(source.get("delivery", "foreground"))[:40],
        "generation_ms": _milliseconds("generation_ms"),
        "prefetch_wait_ms": _milliseconds("prefetch_wait_ms"),
        "recorded_at": time.time(),
    }
