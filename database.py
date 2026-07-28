"""Supabase persistence and recovery for HireSense interviews."""

from __future__ import annotations

import re
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from supabase_backend import SupabaseError, SupabaseGateway
from supabase_backend import is_configured as backend_is_configured

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hiresense-db")
_SAFE_FILE = re.compile(r"[^A-Za-z0-9._-]+")


def is_configured() -> bool:
    return backend_is_configured()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_uuid(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("A valid UUID is required.") from exc


def _epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return time.time()


def _first_row(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


@dataclass
class PendingWrite:
    label: str
    future: Future
    submitted_at: float


@dataclass
class WriteStatus:
    pending: list[PendingWrite]
    completed: list[str]
    errors: list[str]


class DatabaseService:
    """High-level, RLS-protected HireSense database operations."""

    def __init__(
        self,
        *,
        access_token: str,
        user_id: str,
        gateway: SupabaseGateway | None = None,
    ):
        self.user_id = _valid_uuid(user_id)
        self.gateway = gateway or SupabaseGateway.configured(
            access_token=access_token
        )

    def upsert_profile(
        self,
        *,
        email: str,
        full_name: str,
        locale: str,
    ) -> None:
        self.gateway.insert(
            "profiles",
            {
                "id": self.user_id,
                "email": str(email)[:320],
                "full_name": str(full_name)[:120],
                "locale": str(locale)[:20] or "en",
            },
            params={"on_conflict": "id"},
            upsert=True,
        )

    def start_interview(
        self,
        *,
        interview_id: str,
        company_key: str,
        company_name: str,
        job_title: str,
        job_description: str,
        resume_text: str,
        language_key: str,
        language_code: str,
        interview_type: str,
        mode: str,
        model: str,
        total_questions: int,
    ) -> dict[str, Any]:
        interview_id = _valid_uuid(interview_id)
        result = self.gateway.rpc(
            "start_practice_interview",
            {
                "p_interview_id": interview_id,
                "p_company_key": str(company_key)[:80],
                "p_company_name": str(company_name)[:160],
                "p_job_title": str(job_title)[:160] or "Practice role",
                "p_job_description": str(job_description)[:60_000],
                "p_resume_text": str(resume_text)[:60_000],
                "p_language_key": str(language_key)[:20] or "en",
                "p_language_code": str(language_code)[:20] or "en-US",
                "p_interview_type": str(interview_type)[:50],
                "p_mode": str(mode)[:30],
                "p_model": str(model)[:160],
                "p_total_questions": max(1, min(int(total_questions), 50)),
            },
        )
        row = _first_row(result)
        if not row.get("interview_id"):
            raise SupabaseError("Supabase did not create the interview record.")
        return row

    def upsert_turn(self, payload: dict[str, Any]) -> None:
        interview_id = _valid_uuid(payload.get("interview_id", ""))
        turn_index = max(1, int(payload.get("turn_index", 1)))
        self.gateway.insert(
            "interview_turns",
            {
                "interview_id": interview_id,
                "user_id": self.user_id,
                "turn_index": turn_index,
                "question_number": max(
                    1,
                    int(payload.get("question_number", turn_index)),
                ),
                "is_followup": bool(payload.get("is_followup", False)),
                "question_original": str(
                    payload.get("question_original", "")
                )[:8_000],
                "transcript_original": str(
                    payload.get("transcript_original", "")
                )[:20_000],
                "transcript_confirmed": bool(
                    payload.get("transcript_confirmed", True)
                ),
                "language_key": str(payload.get("language_key", "en"))[:20],
                "language_code": str(
                    payload.get("language_code", "en-US")
                )[:20],
                "english_translation": (
                    str(payload["english_translation"])[:20_000]
                    if payload.get("english_translation")
                    else None
                ),
                "transcription_engine": str(
                    payload.get("transcription_engine", "typed")
                )[:80],
                "question_source": str(
                    payload.get("question_source", "model")
                )[:80],
                "speech_stats": (
                    payload.get("speech_stats")
                    if isinstance(payload.get("speech_stats"), dict)
                    else {}
                ),
            },
            params={"on_conflict": "interview_id,turn_index"},
            upsert=True,
        )

    def update_progress(
        self,
        *,
        interview_id: str,
        progress: dict[str, Any],
    ) -> None:
        self.gateway.update(
            "interviews",
            {
                "progress": progress,
                "updated_at": _utc_now(),
            },
            filters={"id": f"eq.{_valid_uuid(interview_id)}"},
        )

    def complete_interview(
        self,
        *,
        interview_id: str,
        metrics: dict[str, Any],
        report_markdown: str,
        evidence_assessment: dict[str, Any] | None,
    ) -> None:
        self.gateway.update(
            "interviews",
            {
                "status": "completed",
                "completed_at": _utc_now(),
                "updated_at": _utc_now(),
                "metrics": metrics,
                "report_markdown": str(report_markdown)[:200_000],
                "evidence_assessment": evidence_assessment,
                "progress": {"completed": True},
            },
            filters={"id": f"eq.{_valid_uuid(interview_id)}"},
        )

    def save_assessment(
        self,
        *,
        interview_id: str,
        assessment: dict[str, Any],
        report_markdown: str,
        metrics: dict[str, Any],
    ) -> None:
        interview_id = _valid_uuid(interview_id)
        self.gateway.update(
            "interviews",
            {
                "report_markdown": str(report_markdown)[:200_000],
                "evidence_assessment": assessment,
                "metrics": metrics,
                "updated_at": _utc_now(),
            },
            filters={"id": f"eq.{interview_id}"},
        )

        dimensions = assessment.get("dimensions")
        if not isinstance(dimensions, dict):
            return
        rows = []
        for dimension, data in dimensions.items():
            if not isinstance(data, dict):
                continue
            evidence = data.get("evidence")
            evidence = evidence if isinstance(evidence, list) else []
            first_excerpt = ""
            if evidence and isinstance(evidence[0], dict):
                first_excerpt = str(evidence[0].get("excerpt", ""))[:1_000]
            rows.append(
                {
                    "interview_id": interview_id,
                    "owner_id": self.user_id,
                    "dimension": str(dimension)[:80],
                    "score": data.get("score"),
                    "evidence_excerpt": first_excerpt or None,
                    "evidence": evidence[:4],
                    "reason": str(data.get("reason", ""))[:1_000],
                    "reliability": str(
                        data.get("reliability", "Unavailable")
                    )[:30],
                }
            )
        if rows:
            self.gateway.insert(
                "evaluation_scores",
                rows,
                params={"on_conflict": "interview_id,dimension"},
                upsert=True,
            )

    def upload_resume(
        self,
        *,
        application_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        application_id = _valid_uuid(application_id)
        if not isinstance(content, bytes) or not content:
            raise ValueError("The resume PDF is empty.")
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("The resume PDF is larger than 10 MB.")
        safe_name = _SAFE_FILE.sub("-", Path(filename).name).strip(".-")
        safe_name = (safe_name or "resume.pdf")[:120]
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"
        path = f"{self.user_id}/{application_id}/{safe_name}"
        self.gateway.upload_pdf(path, content)
        self.gateway.update(
            "applications",
            {"resume_path": path, "updated_at": _utc_now()},
            filters={"id": f"eq.{application_id}"},
        )
        return path

    def load_history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        interviews = self.gateway.select(
            "interviews",
            params={
                "select": (
                    "id,interview_type,company_key,language_key,language_code,"
                    "mode,status,model,total_questions,started_at,completed_at,"
                    "report_markdown,evidence_assessment,metrics"
                ),
                "owner_id": f"eq.{self.user_id}",
                "status": "eq.completed",
                "order": "completed_at.desc",
                "limit": str(max(1, min(int(limit), 100))),
            },
        )
        if not interviews:
            return []

        ids = [str(item["id"]) for item in interviews if item.get("id")]
        turns = self.gateway.select(
            "interview_turns",
            params={
                "select": (
                    "interview_id,turn_index,question_number,is_followup,"
                    "question_original,transcript_original,language_key,"
                    "language_code,transcription_engine,question_source,"
                    "speech_stats,created_at"
                ),
                "interview_id": f"in.({','.join(ids)})",
                "order": "turn_index.asc",
            },
        )
        turns_by_interview: dict[str, list[dict[str, Any]]] = {}
        for turn in turns:
            turns_by_interview.setdefault(str(turn.get("interview_id")), []).append(
                turn
            )

        history = []
        for interview in interviews:
            interview_id = str(interview.get("id", ""))
            interview_turns = turns_by_interview.get(interview_id, [])
            history.append(
                {
                    "id": interview_id,
                    "timestamp": interview.get("completed_at")
                    or interview.get("started_at")
                    or _utc_now(),
                    "interview_type": interview.get("interview_type", "Mixed"),
                    "company": interview.get("company_key", "general"),
                    "language": interview.get("language_key", "en"),
                    "language_code": interview.get(
                        "language_code",
                        "en-US",
                    ),
                    "questions": [
                        {
                            "question": turn.get("question_original", ""),
                            "answer": turn.get("transcript_original", ""),
                            "question_number": turn.get("question_number"),
                            "is_followup": bool(turn.get("is_followup")),
                        }
                        for turn in interview_turns
                    ],
                    "metrics": interview.get("metrics")
                    if isinstance(interview.get("metrics"), dict)
                    else {},
                    "report": interview.get("report_markdown", ""),
                    "evidence_assessment": interview.get("evidence_assessment"),
                    "source": "supabase",
                }
            )
        return history

    def load_recoverable_interview(self) -> dict[str, Any] | None:
        rows = self.gateway.select(
            "interviews",
            params={
                "select": (
                    "id,application_id,interview_type,company_key,language_key,"
                    "language_code,mode,model,total_questions,started_at,progress"
                ),
                "owner_id": f"eq.{self.user_id}",
                "status": "eq.in_progress",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )
        if not rows:
            return None
        interview = rows[0]
        application_id = str(interview.get("application_id", ""))
        applications = self.gateway.select(
            "applications",
            params={
                "select": "id,job_id,resume_text",
                "id": f"eq.{application_id}",
                "limit": "1",
            },
        )
        application = applications[0] if applications else {}
        job_id = str(application.get("job_id", ""))
        jobs = self.gateway.select(
            "jobs",
            params={
                "select": "id,title,company_key,company_name,description",
                "id": f"eq.{job_id}",
                "limit": "1",
            },
        )
        job = jobs[0] if jobs else {}
        interview_id = str(interview.get("id", ""))
        turns = self.gateway.select(
            "interview_turns",
            params={
                "select": (
                    "turn_index,question_number,is_followup,question_original,"
                    "transcript_original,question_source,speech_stats,created_at"
                ),
                "interview_id": f"eq.{interview_id}",
                "order": "turn_index.asc",
            },
        )

        conversation: list[dict[str, Any]] = []
        for turn in turns:
            timestamp = _epoch(turn.get("created_at"))
            conversation.append(
                {
                    "role": "assistant",
                    "content": turn.get("question_original", ""),
                    "timestamp": timestamp,
                    "is_followup": bool(turn.get("is_followup")),
                    "generation_source": turn.get("question_source", "model"),
                }
            )
            conversation.append(
                {
                    "role": "user",
                    "content": turn.get("transcript_original", ""),
                    "timestamp": timestamp,
                    "speech_stats": turn.get("speech_stats") or {},
                }
            )

        return {
            "id": interview_id,
            "application_id": application_id,
            "job_id": job_id,
            "target_role": job.get("title", "Practice role"),
            "company": interview.get("company_key")
            or job.get("company_key")
            or "general",
            "resume_text": application.get("resume_text", ""),
            "job_description": job.get("description", ""),
            "interview_type": interview.get("interview_type", "Mixed"),
            "language": interview.get("language_key", "en"),
            "language_code": interview.get("language_code", "en-US"),
            "mode": interview.get("mode", "text"),
            "model": interview.get("model", ""),
            "total_questions": interview.get("total_questions", 5),
            "started_at": interview.get("started_at"),
            "progress": (
                interview.get("progress")
                if isinstance(interview.get("progress"), dict)
                else {}
            ),
            "conversation": conversation,
            "turn_count": len(turns),
        }

    def abandon_interview(self, *, interview_id: str) -> None:
        self.gateway.update(
            "interviews",
            {
                "status": "abandoned",
                "updated_at": _utc_now(),
                "progress": {"abandoned": True},
            },
            filters={"id": f"eq.{_valid_uuid(interview_id)}"},
        )

    def delete_all_history(self) -> None:
        applications: list[dict[str, Any]] = []
        offset = 0
        while True:
            batch = self.gateway.select(
                "applications",
                params={
                    "select": "id,job_id,resume_path",
                    "candidate_id": f"eq.{self.user_id}",
                    "order": "created_at.asc",
                    "limit": "1000",
                    "offset": str(offset),
                },
            )
            applications.extend(batch)
            if len(batch) < 1000:
                break
            offset += len(batch)
            if offset >= 100_000:
                raise SupabaseError(
                    "History deletion exceeded the supported batch limit."
                )
        resume_paths = [
            str(item["resume_path"])
            for item in applications
            if item.get("resume_path")
        ]
        for start in range(0, len(resume_paths), 100):
            self.gateway.remove_pdfs(resume_paths[start : start + 100])
        self.gateway.insert(
            "audit_events",
            {
                "actor_id": self.user_id,
                "event_type": "interview_history_deleted",
                "entity_type": "interviews",
                "metadata": {"requested_at": _utc_now()},
            },
        )
        self.gateway.delete(
            "applications",
            filters={"candidate_id": f"eq.{self.user_id}"},
        )
        self.gateway.delete(
            "jobs",
            filters={
                "owner_id": f"eq.{self.user_id}",
                "status": "eq.practice",
            },
        )


def enqueue_operation(
    label: str,
    *,
    access_token: str,
    user_id: str,
    operation: str,
    payload: dict[str, Any],
    depends_on: Future | None = None,
) -> PendingWrite:
    """Run a bounded database write outside the voice response path."""
    allowed: dict[str, Callable[..., Any]] = {
        "upsert_turn": DatabaseService.upsert_turn,
        "update_progress": DatabaseService.update_progress,
        "complete_interview": DatabaseService.complete_interview,
        "save_assessment": DatabaseService.save_assessment,
        "upload_resume": DatabaseService.upload_resume,
        "abandon_interview": DatabaseService.abandon_interview,
    }
    if operation not in allowed:
        raise ValueError(f"Unsupported background database operation: {operation}")

    def _run() -> Any:
        if depends_on is not None:
            try:
                depends_on.result()
            except Exception:
                # Preserve ordering without making one failed write suppress all
                # later idempotent writes.
                pass
        service = DatabaseService(
            access_token=access_token,
            user_id=user_id,
        )
        return allowed[operation](service, **payload)

    return PendingWrite(
        label=label,
        future=_EXECUTOR.submit(_run),
        submitted_at=time.time(),
    )


def collect_writes(items: list[PendingWrite]) -> WriteStatus:
    pending: list[PendingWrite] = []
    completed: list[str] = []
    errors: list[str] = []
    for item in items:
        if not item.future.done():
            pending.append(item)
            continue
        try:
            item.future.result()
            completed.append(item.label)
        except Exception as exc:
            errors.append(f"{item.label}: {exc}")
    return WriteStatus(pending=pending, completed=completed, errors=errors)


def flush_writes(
    items: list[PendingWrite],
    *,
    timeout_seconds: float = 2.0,
) -> WriteStatus:
    futures = [item.future for item in items if not item.future.done()]
    if futures:
        wait(futures, timeout=max(0.0, min(float(timeout_seconds), 5.0)))
    return collect_writes(items)
