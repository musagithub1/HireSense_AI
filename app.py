"""HireSense AI live voice interview-practice application.

The public product has one focused path: add resume and job context, complete
a personalized live voice interview, and receive transcript-grounded feedback.
"""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

import streamlit as st

# ============================================================================
# IMPORTANT: Load .env file FIRST before any other imports
# ============================================================================
import config  # This loads the .env file automatically

# Keep the interface available when the model service is not configured.
# Interview questions can still use the disclosed built-in bank, while model
# features report that they are unavailable.
CONFIG_IS_VALID, CONFIG_MESSAGE = config.validate_config()

import analytics_dashboard as analytics
import auth
import coding_whiteboard
import company_prep
import confidence_model
import database
import evidence_scoring
import followup_questions
import interview_arena as arena
import interview_flow

# New feature imports
import language_support
import latency_optimizer
import live_copilot
import nonverbal_analysis
import persistence_component as persistence
import skill_gap_analysis
import supabase_auth
import ui_theme
import video_recording
import voice_input_component as voice_input
import webcam_component as webcam

# ============================================================================
# Interview Types
# ============================================================================

INTERVIEW_TYPES = {
    "Technical": {
        "icon": "💻",
        "description": "Coding, system design, and technical problem-solving",
        "focus": [
            "Data structures",
            "Algorithms",
            "System design",
            "Technical projects",
        ],
    },
    "Behavioral": {
        "icon": "🤝",
        "description": "Soft skills, teamwork, and past experiences (STAR method)",
        "focus": ["Leadership", "Teamwork", "Conflict resolution", "Problem-solving"],
    },
    "HR": {
        "icon": "👔",
        "description": "Culture fit, career goals, and company alignment",
        "focus": ["Career goals", "Motivation", "Company fit", "Expectations"],
    },
    "Case Study": {
        "icon": "📊",
        "description": "Business scenarios and analytical thinking",
        "focus": ["Analysis", "Problem-solving", "Business acumen", "Communication"],
    },
    "Mixed": {
        "icon": "🎯",
        "description": "Comprehensive interview covering all aspects",
        "focus": [
            "Technical skills",
            "Soft skills",
            "Culture fit",
            "Overall assessment",
        ],
    },
}

LIVE_VOICE_MODE = "🎙️ Live Voice Interview"
LIVE_VOICE_QUESTION_COUNT = interview_flow.DEFAULT_MAIN_QUESTION_COUNT


# ============================================================================
# Helper Functions
# ============================================================================


def display_streaming_response(stream_generator, status_sink: dict | None = None):
    """Display streaming response with per-agent pipeline traces."""
    response_text = ""

    # Track per-agent trace content
    agent_traces = {}  # agent_name -> list of trace strings
    agent_status = {}  # agent_name -> "running" | "done"
    agent_order = []  # maintain insertion order

    pipeline_container = None
    pipeline_placeholder = None
    response_placeholder = st.empty()

    def _render_pipeline():
        """Re-render the full pipeline view."""
        if pipeline_placeholder is None:
            return
        md = ""
        for agent_name in agent_order:
            status = agent_status.get(agent_name, "running")
            traces = agent_traces.get(agent_name, [])

            status_label = "Complete" if status == "done" else "Working"
            md += f"**{agent_name}** · {status_label}\n\n"
            for t in traces:
                md += f"{t}\n"
            md += "\n"

        pipeline_placeholder.markdown(md)

    for chunk in stream_generator:
        if isinstance(chunk, dict):
            chunk_type = chunk.get("type", "")
            agent_name = chunk.get("agent", "")
            # Create the pipeline expander on first trace
            if pipeline_container is None and chunk_type in (
                "trace",
                "tool_use",
                "agent_done",
                "pipeline_start",
            ):
                pipeline_container = st.expander(
                    "How HireSense prepared this question", expanded=False
                )
                pipeline_placeholder = pipeline_container.empty()

            if chunk_type == "pipeline_start":
                agent_traces["Interview engine"] = [chunk.get("content", "")]
                agent_status["Interview engine"] = "done"
                if "Interview engine" not in agent_order:
                    agent_order.append("Interview engine")
                _render_pipeline()

            elif chunk_type == "trace":
                display_name = agent_name
                if display_name not in agent_order:
                    agent_order.append(display_name)
                    agent_traces[display_name] = []
                    agent_status[display_name] = "running"
                agent_traces[display_name].append(f"- {chunk.get('content', '')}")
                _render_pipeline()

            elif chunk_type == "tool_use":
                display_name = agent_name
                if display_name not in agent_order:
                    agent_order.append(display_name)
                    agent_traces[display_name] = []
                agent_traces[display_name].append(
                    f"- **{chunk.get('tool', '')}:** {chunk.get('result', '')}"
                )
                _render_pipeline()

            elif chunk_type == "agent_done":
                display_name = agent_name
                agent_status[display_name] = "done"
                if display_name in agent_traces:
                    agent_traces[display_name].append(
                        f"- **Complete:** {chunk.get('summary', '')}"
                    )
                _render_pipeline()

            elif chunk_type == "question_chunk":
                response_text += chunk["content"]
                response_placeholder.markdown(response_text + "▌")

            elif chunk_type == "question_generation_status":
                if status_sink is not None:
                    status_sink.update(chunk)
                if chunk.get("source") == "built_in_fallback":
                    st.warning(
                        "The live AI question service was unavailable, so HireSense "
                        "used a built-in interview question. You can retry the AI question."
                    )

        elif isinstance(chunk, str):
            response_text += chunk
            response_placeholder.markdown(response_text + "▌")

    response_placeholder.markdown(response_text)
    return response_text


def init_session_state():
    """Initialize session state for the interview."""
    defaults = {
        "logged_in": False,
        "uid": None,
        "email": None,
        "display_name": None,
        "supabase_access_token": None,
        "supabase_refresh_token": None,
        "supabase_expires_at": None,
        "interview_started": False,
        "interview_resume_text": None,
        "interview_jd_text": None,
        "interview_rag_context": None,
        "interview_history": [],
        "interview_stress_timeline": [],
        "current_question_num": 0,
        "total_questions": LIVE_VOICE_QUESTION_COUNT,
        "current_emotional_state": "neutral",
        "interview_complete": False,
        "tts_enabled": True,
        "webcam_enabled": False,
        "facial_signal_consent": False,
        "facial_support_questions": [],
        "voice_input_enabled": True,
        "current_stress_level": None,
        "emotion_reading": None,
        "manual_stress_override": None,
        "interview_start_time": None,
        "interview_report": None,
        "awaiting_question": True,
        "current_question_text": None,
        "current_question_source": None,
        "current_question_status": None,
        "tts_played": False,
        "_interview_orchestrator": None,
        "_next_question_prefetch": None,
        "_latency_session_id": None,
        "latency_samples": [],
        "interview_type": "Mixed",
        "interview_mode": LIVE_VOICE_MODE,
        "target_role": "",
        "question_bank": [],
        "current_voice_answer": "",
        "page": "interview",
        # New feature states
        "selected_language": "en",
        "selected_company": "general",
        "video_recording_enabled": False,
        "followup_enabled": True,
        "awaiting_followup": False,
        "followup_count": 0,
        "total_followups_asked": 0,
        "max_total_followups": interview_flow.MAX_TOTAL_FOLLOWUPS,
        "max_followups": 1,
        "current_question_is_followup": False,
        "current_question_revision": 0,
        "last_followup_decision": None,
        "rephrase_notice": None,
        "evidence_assessment": None,
        "evidence_assessment_error": None,
        "skill_analysis_done": False,
        "skill_analysis_result": None,
        # New feature states for Copilot and Coding
        "copilot_enabled": False,
        "coding_mode_enabled": False,
        "current_problem": None,
        "coding_language": "python",
        # Non-verbal analysis states
        "nonverbal_analysis_done": False,
        "show_nonverbal_analysis": False,
        "nonverbal_results": None,
        "nonverbal_detailed_report": None,
        # Supabase persistence and recovery
        "active_interview_id": None,
        "active_application_id": None,
        "active_job_id": None,
        "_database_sync_ready": False,
        "_database_restored": False,
        "_database_pending_writes": [],
        "_database_sync_error": None,
        "_database_completion_queued_for": None,
        "_recoverable_interview": None,
        "_recoverable_interview_loaded": False,
        "_resume_upload_bytes": None,
        "_resume_upload_name": None,
        "save_resume_file": True,
        "resume_saved_to_supabase": False,
        "resume_storage_status": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _active_stress_reading() -> dict | None:
    """Return the current real or explicitly enabled developer reading."""
    manual_override = st.session_state.get("manual_stress_override")
    if manual_override is not None:
        return {
            "stress_level": float(manual_override),
            "source": "developer_override",
            "sample_count": 1,
        }

    reading = st.session_state.get("emotion_reading")
    if webcam.reading_is_usable(reading):
        return {
            "stress_level": float(reading["stress_score"]),
            "source": "trained_facial_model",
            "sample_count": int(reading.get("sample_count", 0)),
            "measured_at": reading.get("measured_at"),
        }
    return None


def record_current_stress(question_num: int) -> bool:
    """Record a genuine stress reading, never a neutral placeholder."""
    reading = _active_stress_reading()
    if reading is None:
        return False

    st.session_state["interview_stress_timeline"].append(
        {
            "timestamp": time.time() - st.session_state["interview_start_time"],
            "stress_level": reading["stress_level"],
            "question_num": question_num,
            "source": reading["source"],
            "sample_count": reading.get("sample_count", 0),
            "measured_at": reading.get("measured_at"),
        }
    )
    return True


def _facial_interviewer_state(question_num: int) -> str:
    """Return a consented tone hint without changing interview difficulty."""
    if not st.session_state.get("facial_signal_consent", False):
        return "neutral"

    state = webcam.interviewer_support_state(
        st.session_state.get("interview_stress_timeline", [])
    )
    if state == "stress_signal":
        used_questions = st.session_state.setdefault(
            "facial_support_questions",
            [],
        )
        if question_num not in used_questions:
            used_questions.append(question_num)
    return state


def get_ui_text(key: str) -> str:
    """Get translated UI text based on selected language."""
    return language_support.get_ui_text(
        key, st.session_state.get("selected_language", "en")
    )


def extract_uploaded_pdf(uploaded_file, document_name: str) -> str:
    """Read an uploaded PDF without allowing one bad file to crash the app."""
    try:
        return arena.extract_pdf_text(uploaded_file.getvalue())
    except ValueError as exc:
        st.error(f"{document_name}: {exc}")
    except Exception as exc:
        st.error(
            f"{document_name} could not be read "
            f"({exc.__class__.__name__}). Try another PDF or paste the text."
        )
    return ""


def _database_session_ready() -> bool:
    """Return whether RLS-authenticated Supabase calls can be made."""
    return bool(
        database.is_configured()
        and st.session_state.get("supabase_access_token")
        and st.session_state.get("uid")
    )


def _database_service() -> database.DatabaseService:
    if not _database_session_ready():
        raise RuntimeError("The Supabase database session is not ready.")
    return database.DatabaseService(
        access_token=str(st.session_state["supabase_access_token"]),
        user_id=str(st.session_state["uid"]),
    )


def _queue_database_operation(
    label: str,
    operation: str,
    payload: dict,
) -> None:
    """Queue one idempotent write without delaying the interview response."""
    if not (
        _database_session_ready()
        and st.session_state.get("_database_sync_ready")
    ):
        return
    try:
        existing_writes = st.session_state.setdefault(
            "_database_pending_writes",
            [],
        )
        dependency = (
            existing_writes[-1].future if existing_writes else None
        )
        pending = database.enqueue_operation(
            label,
            access_token=str(st.session_state["supabase_access_token"]),
            user_id=str(st.session_state["uid"]),
            operation=operation,
            payload=payload,
            depends_on=dependency,
        )
    except Exception as exc:
        st.session_state["_database_sync_error"] = str(exc)[:500]
        return
    existing_writes.append(pending)


def _collect_database_writes() -> None:
    """Collect finished background writes and retain bounded error state."""
    items = st.session_state.get("_database_pending_writes", [])
    if not items:
        return
    status = database.collect_writes(items)
    st.session_state["_database_pending_writes"] = status.pending
    if status.errors:
        st.session_state["_database_sync_error"] = status.errors[-1][:500]


def _progress_snapshot() -> dict:
    """Return only the state needed to safely resume the current interview."""
    return {
        "current_question_num": int(
            st.session_state.get("current_question_num", 1)
        ),
        "awaiting_question": bool(
            st.session_state.get("awaiting_question", True)
        ),
        "awaiting_followup": bool(
            st.session_state.get("awaiting_followup", False)
        ),
        "followup_count": int(st.session_state.get("followup_count", 0)),
        "last_followup_decision": (
            st.session_state.get("last_followup_decision")
            if isinstance(
                st.session_state.get("last_followup_decision"),
                dict,
            )
            else None
        ),
        "total_questions": int(
            st.session_state.get(
                "total_questions",
                LIVE_VOICE_QUESTION_COUNT,
            )
        ),
        "total_followups_asked": int(
            st.session_state.get("total_followups_asked", 0)
        ),
        "updated_at_epoch": time.time(),
    }


def _queue_progress_sync() -> None:
    interview_id = st.session_state.get("active_interview_id")
    if interview_id:
        _queue_database_operation(
            "Save interview recovery state",
            "update_progress",
            {
                "interview_id": interview_id,
                "progress": _progress_snapshot(),
            },
        )


def _persist_confirmed_turn(
    answer: str,
    *,
    is_followup: bool,
    transcription_engine: str,
    speech_stats: dict | None = None,
) -> None:
    """Save only a submitted answer, never a partial microphone transcript."""
    interview_id = st.session_state.get("active_interview_id")
    if not interview_id:
        return
    turn_index = sum(
        1
        for entry in st.session_state.get("interview_history", [])
        if entry.get("role") == "user"
    )
    _queue_database_operation(
        f"Save confirmed answer {turn_index}",
        "upsert_turn",
        {
            "interview_id": interview_id,
            "turn_index": turn_index,
            "question_number": st.session_state.get("current_question_num", 1),
            "is_followup": is_followup,
            "question_original": st.session_state.get(
                "current_question_text",
                "",
            ),
            "transcript_original": answer,
            "transcript_confirmed": True,
            "language_key": st.session_state.get("selected_language", "en"),
            "language_code": language_support.get_speech_recognition_code(
                st.session_state.get("selected_language", "en")
            ),
            "english_translation": None,
            "transcription_engine": transcription_engine,
            "question_source": st.session_state.get(
                "current_question_source",
                "model",
            ),
            "speech_stats": speech_stats or {},
        },
    )


def _record_metrics(qa_pairs: list[dict], duration: str) -> dict:
    assessment = st.session_state.get("evidence_assessment") or {}
    delivery_summary = confidence_model.summarize_interview_delivery(
        st.session_state.get("interview_history", [])
    )
    facial_summary = webcam.summarize_facial_expression_timeline(
        st.session_state.get("interview_stress_timeline", [])
    )
    stress_values = [
        float(item["stress_level"])
        for item in st.session_state.get("interview_stress_timeline", [])
        if isinstance(item.get("stress_level"), (int, float))
        and not isinstance(item.get("stress_level"), bool)
        and 0 <= float(item["stress_level"]) <= 1
        and item.get("source") == "trained_facial_model"
    ]
    return {
        "evidence_score_5": assessment.get("overall_score_5"),
        "evidence_reliability": assessment.get(
            "overall_reliability",
            "Unavailable",
        ),
        "scoring_coverage": assessment.get("coverage_percent", 0),
        "optional_facial_readings_count": len(stress_values),
        "duration": duration,
        "total_questions": st.session_state.get(
            "total_questions",
            LIVE_VOICE_QUESTION_COUNT,
        ),
        "questions_answered": len(qa_pairs),
        "delivery_confidence": delivery_summary,
        "facial_expression_summary": facial_summary,
        "facial_support_questions": list(
            st.session_state.get("facial_support_questions", [])
        ),
    }


def _start_database_interview(interview_id: str) -> None:
    """Create the normalized job/application/interview bundle in one RPC."""
    st.session_state["_database_sync_ready"] = False
    if not _database_session_ready():
        return
    company_key = st.session_state.get("selected_company", "general")
    company_name = company_prep.get_company_info(company_key)["name"]
    mode = (
        "live_voice"
        if st.session_state.get("interview_mode") == "🎙️ Live Voice Interview"
        else "text"
    )
    try:
        service = _database_service()
        recoverable = st.session_state.get("_recoverable_interview")
        if (
            isinstance(recoverable, dict)
            and recoverable.get("id")
            and str(recoverable["id"]) != str(interview_id)
        ):
            try:
                service.abandon_interview(interview_id=recoverable["id"])
                st.session_state["_recoverable_interview"] = None
            except Exception:
                pass

        row = service.start_interview(
            interview_id=interview_id,
            company_key=company_key,
            company_name=company_name,
            job_title=st.session_state.get("target_role") or "Practice role",
            job_description=st.session_state.get("interview_jd_text") or "",
            resume_text=st.session_state.get("interview_resume_text") or "",
            language_key=st.session_state.get("selected_language", "en"),
            language_code=language_support.get_speech_recognition_code(
                st.session_state.get("selected_language", "en")
            ),
            interview_type=st.session_state.get("interview_type", "Mixed"),
            mode=mode,
            model=config.get_openrouter_model(),
            total_questions=st.session_state.get(
                "total_questions",
                LIVE_VOICE_QUESTION_COUNT,
            ),
        )
        st.session_state["active_application_id"] = row.get("application_id")
        st.session_state["active_job_id"] = row.get("job_id")
        st.session_state["_database_sync_ready"] = True
        st.session_state["_database_sync_error"] = None

        st.session_state["resume_saved_to_supabase"] = True
        st.session_state["resume_storage_status"] = "text_saved"
        if (
            st.session_state.get("_resume_upload_bytes")
            and row.get("application_id")
        ):
            try:
                service.upload_resume(
                    application_id=row["application_id"],
                    filename=st.session_state.get("_resume_upload_name")
                    or "resume.pdf",
                    content=st.session_state["_resume_upload_bytes"],
                )
                st.session_state["resume_storage_status"] = (
                    "text_and_private_pdf_saved"
                )
            except Exception as exc:
                st.session_state["_database_sync_error"] = (
                    "The extracted resume text was saved, but the private PDF "
                    f"upload could not finish: {exc}"
                )[:500]
    except Exception as exc:
        st.session_state["resume_saved_to_supabase"] = False
        st.session_state["resume_storage_status"] = "save_failed"
        st.session_state["_database_sync_error"] = str(exc)[:500]


def _merge_interview_history(
    local_history: list[dict],
    cloud_history: list[dict],
) -> list[dict]:
    """Merge browser migration data with Supabase as the source of truth by id."""
    merged: dict[str, dict] = {}
    order: list[str] = []
    for item in local_history + cloud_history:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or uuid4())
        if item_id not in merged:
            order.append(item_id)
        merged[item_id] = item
    return [merged[item_id] for item_id in order][-100:]


def _restore_database_data() -> None:
    """Load cloud history and detect an unfinished interview once per login."""
    if (
        not _database_session_ready()
        or st.session_state.get("_database_restored")
    ):
        return
    try:
        service = _database_service()
        service.upsert_profile(
            email=str(st.session_state.get("email") or ""),
            full_name=str(
                st.session_state.get("display_name") or "HireSense User"
            ),
            locale=str(st.session_state.get("selected_language") or "en"),
        )
        cloud_history = service.load_history()
        st.session_state["question_bank"] = _merge_interview_history(
            st.session_state.get("question_bank", []),
            cloud_history,
        )
        st.session_state["_recoverable_interview"] = (
            service.load_recoverable_interview()
        )
        st.session_state["_recoverable_interview_loaded"] = True
        st.session_state["_database_sync_error"] = None
    except Exception as exc:
        st.session_state["_database_sync_error"] = str(exc)[:500]
    finally:
        st.session_state["_database_restored"] = True


def _resume_recoverable_interview(record: dict) -> None:
    """Restore a confirmed-turn checkpoint from Supabase."""
    resume_text = str(record.get("resume_text", ""))
    job_description = str(record.get("job_description", ""))
    resume_data = arena.parse_resume(resume_text)
    jd_data = arena.parse_job_description(job_description)
    company_key = "general"
    language = str(record.get("language") or "en")
    st.session_state["interview_rag_context"] = (
        f"{arena.build_rag_context(resume_data, jd_data)}\n\n"
        f"{company_prep.get_company_interview_prompt(company_key)}\n\n"
        f"{language_support.get_interview_language_prompt(language)}"
    )

    progress = record.get("progress")
    progress = progress if isinstance(progress, dict) else {}
    base_answers = sum(
        1
        for entry in record.get("conversation", [])
        if entry.get("role") == "assistant" and not entry.get("is_followup")
    )
    current_question = int(
        progress.get("current_question_num") or (base_answers + 1)
    )
    started_at = time.time()
    if isinstance(record.get("started_at"), str):
        try:
            started_at = datetime.fromisoformat(
                record["started_at"].replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            pass

    st.session_state.update(
        {
            "active_interview_id": record.get("id"),
            "active_application_id": record.get("application_id"),
            "active_job_id": record.get("job_id"),
            "_database_sync_ready": True,
            "target_role": record.get("target_role", "Practice role"),
            "interview_resume_text": resume_text,
            "interview_jd_text": job_description,
            "selected_company": "general",
            "selected_language": language,
            "interview_type": "Mixed",
            "interview_mode": LIVE_VOICE_MODE,
            "total_questions": LIVE_VOICE_QUESTION_COUNT,
            "total_followups_asked": int(
                progress.get("total_followups_asked", 0)
            ),
            "max_total_followups": interview_flow.MAX_TOTAL_FOLLOWUPS,
            "followup_enabled": True,
            "tts_enabled": True,
            "voice_input_enabled": True,
            "webcam_enabled": False,
            "video_recording_enabled": False,
            "interview_history": list(record.get("conversation") or []),
            "current_question_num": current_question,
            "interview_started": True,
            "interview_complete": False,
            "awaiting_question": bool(
                progress.get("awaiting_question", True)
            ),
            "awaiting_followup": bool(
                progress.get("awaiting_followup", False)
            ),
            "followup_count": int(progress.get("followup_count", 0)),
            "last_followup_decision": progress.get(
                "last_followup_decision"
            ),
            "current_question_text": None,
            "current_question_source": None,
            "current_question_status": None,
            "current_question_is_followup": False,
            "current_question_revision": 0,
            "interview_report": None,
            "evidence_assessment": None,
            "interview_start_time": started_at,
            "_latency_session_id": uuid4().hex,
            "_recoverable_interview": None,
        }
    )


def save_to_question_bank():
    """Save the current interview to the question bank."""
    if not st.session_state.get("interview_history"):
        return

    qa_pairs = []
    history = st.session_state["interview_history"]
    for i in range(0, len(history) - 1, 2):
        if i + 1 < len(history):
            qa_pairs.append(
                {
                    "question": history[i].get("content", ""),
                    "answer": history[i + 1].get("content", ""),
                }
            )

    assessment = st.session_state.get("evidence_assessment") or {}

    duration = "N/A"
    if st.session_state.get("interview_start_time"):
        elapsed = time.time() - st.session_state["interview_start_time"]
        duration = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

    metrics = _record_metrics(qa_pairs, duration)
    interview_id = str(
        st.session_state.get("active_interview_id") or uuid4()
    )
    st.session_state["active_interview_id"] = interview_id
    interview_record = {
        "id": interview_id,
        "timestamp": datetime.now().astimezone().isoformat(),
        "interview_type": st.session_state.get("interview_type", "Mixed"),
        "company": st.session_state.get("selected_company", "general"),
        "language": st.session_state.get("selected_language", "en"),
        "target_role": st.session_state.get("target_role", "Practice role"),
        "questions": qa_pairs,
        "metrics": metrics,
        "report": st.session_state.get("interview_report", ""),
        "evidence_assessment": assessment or None,
        "source": (
            "supabase"
            if st.session_state.get("_database_sync_ready")
            else "browser"
        ),
    }

    if "question_bank" not in st.session_state:
        st.session_state["question_bank"] = []

    existing_index = next(
        (
            index
            for index, item in enumerate(st.session_state["question_bank"])
            if str(item.get("id")) == interview_id
        ),
        None,
    )
    if existing_index is None:
        st.session_state["question_bank"].append(interview_record)
    else:
        st.session_state["question_bank"][existing_index] = interview_record

    persistence.save_to_browser(
        "interview_history",
        st.session_state["question_bank"],
        key="save_question_bank",
    )

    if (
        st.session_state.get("_database_sync_ready")
        and st.session_state.get("_database_completion_queued_for")
        != interview_id
    ):
        st.session_state["_database_completion_queued_for"] = interview_id
        _queue_database_operation(
            "Complete interview",
            "complete_interview",
            {
                "interview_id": interview_id,
                "metrics": metrics,
                "report_markdown": st.session_state.get(
                    "interview_report",
                    "",
                ),
                "evidence_assessment": assessment or None,
            },
        )


def retry_current_question() -> None:
    """Remove the current generated question and request it again."""
    _cancel_question_prefetch()
    st.session_state["_interview_orchestrator"] = None
    current_question = st.session_state.get("current_question_text")
    history = st.session_state.get("interview_history", [])
    retrying_followup = False
    if (
        current_question
        and history
        and history[-1].get("role") == "assistant"
        and history[-1].get("content") == current_question
    ):
        retrying_followup = bool(history[-1].get("is_followup"))
        history.pop()

    st.session_state["awaiting_question"] = not retrying_followup
    st.session_state["awaiting_followup"] = retrying_followup
    if retrying_followup:
        st.session_state["followup_count"] = max(
            0, st.session_state.get("followup_count", 1) - 1
        )
    st.session_state["current_question_text"] = None
    st.session_state["current_question_source"] = None
    st.session_state["current_question_status"] = None
    st.session_state["current_question_revision"] = (
        st.session_state.get("current_question_revision", 0) + 1
    )
    st.session_state["tts_played"] = False


def _collect_generated_question(generator) -> tuple[str, dict]:
    """Collect a streamed question and its disclosed generation status."""
    text = ""
    status: dict = {}
    for chunk in generator:
        if isinstance(chunk, dict):
            if chunk.get("type") == "question_chunk":
                text += str(chunk.get("content", ""))
            elif chunk.get("type") == "question_generation_status":
                status.update(chunk)
        elif isinstance(chunk, str):
            text += chunk
    return text.strip(), status


def _get_interview_orchestrator():
    """Return a session-scoped orchestrator so caches never cross users."""
    from hiresense_agent import HireSenseOrchestrator

    model_name = config.get_openrouter_model()
    temperature = 0.7
    orchestrator = st.session_state.get("_interview_orchestrator")
    if (
        orchestrator is None
        or getattr(orchestrator, "model_name", None) != model_name
        or getattr(orchestrator, "temperature", None) != temperature
    ):
        orchestrator = HireSenseOrchestrator(model_name, temperature)
        st.session_state["_interview_orchestrator"] = orchestrator
    return orchestrator


def _cancel_question_prefetch() -> None:
    """Discard any future question that no longer matches the interview state."""
    latency_optimizer.cancel_question_prefetch(
        st.session_state.get("_next_question_prefetch")
    )
    st.session_state["_next_question_prefetch"] = None


def _schedule_next_base_question(*, target_question: int | None = None) -> None:
    """Generate a base question before its turn reaches the critical path."""
    current_question = int(st.session_state.get("current_question_num", 1))
    total_questions = int(st.session_state.get("total_questions", 1))
    target_question = (
        current_question + 1
        if target_question is None
        else max(1, int(target_question))
    )
    if (
        target_question > total_questions
        or st.session_state.get("interview_complete")
        or not CONFIG_IS_VALID
    ):
        return

    existing = st.session_state.get("_next_question_prefetch")
    if (
        isinstance(existing, latency_optimizer.QuestionPrefetch)
        and existing.target_question == target_question
    ):
        return
    _cancel_question_prefetch()

    session_id = st.session_state.get("_latency_session_id")
    if not session_id:
        session_id = uuid4().hex
        st.session_state["_latency_session_id"] = session_id

    rag_context = str(st.session_state.get("interview_rag_context", ""))
    history = [
        dict(entry) for entry in st.session_state.get("interview_history", [])
    ]
    interview_type = st.session_state.get("interview_type", "Mixed")
    company = st.session_state.get("selected_company", "general")
    total = st.session_state.get(
        "total_questions",
        LIVE_VOICE_QUESTION_COUNT,
    )
    key = latency_optimizer.question_cache_key(
        session_id=session_id,
        target_question=target_question,
        interview_type=interview_type,
        company=company,
        rag_context=rag_context,
        conversation_history=history,
    )
    model_name = config.get_openrouter_model()
    orchestrator = _get_interview_orchestrator()

    def _generator_factory():
        return arena.generate_interview_question(
            rag_context,
            history,
            "neutral",
            target_question,
            total,
            interview_type,
            company=company,
            model_name=model_name,
            temperature=orchestrator.temperature,
            orchestrator=orchestrator,
        )

    st.session_state["_next_question_prefetch"] = (
        latency_optimizer.schedule_question_prefetch(
            target_question=target_question,
            cache_key=key,
            generator_factory=_generator_factory,
        )
    )


def _resolve_prefetched_base_question(
    question_number: int,
) -> latency_optimizer.PrefetchResolution:
    """Hand a prepared base question to the UI with a bounded wait."""
    job = st.session_state.get("_next_question_prefetch")
    if not isinstance(job, latency_optimizer.QuestionPrefetch):
        return latency_optimizer.PrefetchResolution("miss", None, 0)
    resolution = latency_optimizer.resolve_question_prefetch(
        job,
        target_question=question_number,
        cache_key=job.cache_key,
    )
    if resolution.state != "miss":
        _cancel_question_prefetch()
    if resolution.state in {"timeout", "error"}:
        # A provider call may still be unwinding in its worker. Use a new
        # session client for later requests instead of sharing one concurrently.
        st.session_state["_interview_orchestrator"] = None
    return resolution


def _record_question_latency(
    *,
    question_number: int,
    is_followup: bool,
    status: dict | None,
) -> None:
    """Store a small content-free rolling latency log for diagnostics."""
    samples = st.session_state.setdefault("latency_samples", [])
    samples.append(
        latency_optimizer.latency_event(
            question_number=question_number,
            is_followup=is_followup,
            status=status,
        )
    )
    del samples[:-50]


def _record_client_latency(
    *,
    question_number: int,
    latency: dict | None,
) -> None:
    """Store sanitized browser timing values returned by the voice component."""
    if not isinstance(latency, dict):
        return
    sample = {
        "question_number": max(1, int(question_number)),
        "phase": "voice_capture",
        "recorded_at": time.time(),
    }
    sample.update(latency)
    samples = st.session_state.setdefault("latency_samples", [])
    samples.append(sample)
    del samples[:-50]


def _clear_current_turn() -> None:
    """Clear server-side turn state while keeping the browser component alive."""
    st.session_state["current_question_text"] = None
    st.session_state["current_question_source"] = None
    st.session_state["current_question_status"] = None
    st.session_state["current_question_is_followup"] = False
    st.session_state["rephrase_notice"] = None
    st.session_state["current_question_revision"] = (
        st.session_state.get("current_question_revision", 0) + 1
    )
    st.session_state["tts_played"] = False
    st.session_state["current_voice_answer"] = ""


def _followup_decision(question: str, answer: str) -> dict:
    """Choose one evidence-seeking follow-up without an extra model call."""
    phase = interview_flow.phase_for_question(
        st.session_state["current_question_num"],
        st.session_state["total_questions"],
    )
    if not phase.allow_followup:
        return {
            "should_followup": False,
            "reason": f"The {phase.name.lower()} stage moves forward naturally",
        }
    if st.session_state.get("total_followups_asked", 0) >= st.session_state.get(
        "max_total_followups",
        interview_flow.MAX_TOTAL_FOLLOWUPS,
    ):
        return {
            "should_followup": False,
            "reason": "The interview has enough focused follow-up evidence",
        }
    started = st.session_state.get("interview_start_time") or time.time()
    return followup_questions.should_ask_followup(
        answer=answer,
        question=question,
        question_number=st.session_state["current_question_num"],
        total_questions=st.session_state["total_questions"],
        time_elapsed_seconds=max(0.0, time.time() - started),
        max_followups_per_question=st.session_state.get("max_followups", 1),
        current_followups=st.session_state.get("followup_count", 0),
        interview_type=st.session_state.get("interview_type", "Mixed"),
    )


def _advance_after_answer(answer: str, *, answered_followup: bool) -> dict:
    """Advance to a targeted follow-up or the next base question."""
    current_question = st.session_state.get("current_question_text", "")
    decision = {
        "should_followup": False,
        "reason": "The targeted follow-up was completed",
    }

    if not answered_followup and st.session_state.get("followup_enabled", True):
        decision = _followup_decision(current_question, answer)

    if decision.get("should_followup"):
        st.session_state["last_followup_decision"] = decision
        st.session_state["awaiting_followup"] = True
        st.session_state["awaiting_question"] = False
    else:
        st.session_state["current_question_num"] += 1
        st.session_state["awaiting_question"] = True
        st.session_state["awaiting_followup"] = False
        st.session_state["last_followup_decision"] = None

    _clear_current_turn()
    if st.session_state["current_question_num"] > st.session_state["total_questions"]:
        st.session_state["interview_complete"] = True
        _cancel_question_prefetch()
        save_to_question_bank()
    else:
        _queue_progress_sync()
    return decision


def _handle_live_voice_control_action(action: str) -> bool:
    """Handle non-answer controls without falling through to answer handling."""
    if action == "end":
        st.session_state["interview_complete"] = True
        _cancel_question_prefetch()
        save_to_question_bank()
        st.rerun()
        return True

    if action == "rephrase":
        _rephrase_current_question()
        st.rerun()
        return True

    return False


def _rephrase_current_question() -> dict:
    """Apply the accessibility rephrase action to the current question."""
    current = st.session_state.get("current_question_text", "")
    language_name = language_support.get_language_info(
        st.session_state.get("selected_language", "en")
    ).get("name", "English")
    result = arena.rephrase_interview_question(
        current,
        language_name=language_name,
    )
    st.session_state["current_question_revision"] = (
        st.session_state.get("current_question_revision", 0) + 1
    )

    if result.get("source") != "model_rephrase":
        st.session_state["rephrase_notice"] = (
            "Rephrasing is temporarily unavailable. The original question is unchanged."
        )
        return result

    rewritten = result["question"]
    history = st.session_state.get("interview_history", [])
    if (
        history
        and history[-1].get("role") == "assistant"
        and history[-1].get("content") == current
    ):
        history[-1].setdefault("original_content", current)
        history[-1]["content"] = rewritten
        history[-1]["rephrased_for_accessibility"] = True
    st.session_state["current_question_text"] = rewritten
    st.session_state["current_question_source"] = "model_rephrase"
    st.session_state["rephrase_notice"] = "Question rephrased with the same assessment intent."
    return result


def _update_saved_assessment(assessment: dict, report: str) -> None:
    """Attach a completed assessment to the current saved interview."""
    history = st.session_state.get("question_bank", [])
    if not history:
        return
    current = history[-1]
    current["evidence_assessment"] = assessment
    current["report"] = report
    current.setdefault("metrics", {}).update(
        {
            "evidence_score_5": assessment.get("overall_score_5"),
            "evidence_reliability": assessment.get(
                "overall_reliability", "Unavailable"
            ),
            "scoring_coverage": assessment.get("coverage_percent", 0),
        }
    )
    persistence.save_to_browser(
        "interview_history",
        history,
        key="save_question_bank_assessment",
    )
    interview_id = st.session_state.get("active_interview_id")
    if interview_id and st.session_state.get("_database_sync_ready"):
        metrics = current.get("metrics", {})
        _queue_database_operation(
            "Save evidence assessment",
            "save_assessment",
            {
                "interview_id": interview_id,
                "assessment": assessment,
                "report_markdown": report,
                "metrics": metrics,
            },
        )


# ============================================================================
# Page Renderers
# ============================================================================


def _render_legacy_interview_setup():
    """Retain the previous multi-feature setup for migration reference only."""
    has_resume = bool(st.session_state.get("interview_resume_text"))
    has_job_description = bool(st.session_state.get("interview_jd_text"))
    ui_theme.render_page_header(
        "Interview studio",
        "Build a focused practice interview",
        (
            "Add the role context once, choose how you want to practise, and let "
            "HireSense prepare a structured interview around the evidence that matters."
        ),
    )
    ui_theme.render_stepper(
        ui_theme.setup_active_step(
            has_resume=has_resume,
            has_job_description=has_job_description,
        )
    )

    if _database_session_ready() and st.session_state.get(
        "_database_sync_error"
    ):
        st.warning(
            "Cloud sync is unavailable, so HireSense will keep working with "
            "the browser backup. Run the included Supabase migration and verify "
            "the project URL and public key. Details are available in Developer "
            "status when developer mode is enabled."
        )

    recoverable = st.session_state.get("_recoverable_interview")
    if isinstance(recoverable, dict) and recoverable.get("id"):
        with st.container(border=True):
            st.markdown("#### Continue your unfinished interview")
            st.caption(
                f"{recoverable.get('target_role', 'Practice role')} · "
                f"{recoverable.get('turn_count', 0)} confirmed answers saved"
            )
            resume_col, discard_col = st.columns(2)
            with resume_col:
                if st.button(
                    "Resume saved interview",
                    type="primary",
                    width="stretch",
                ):
                    _resume_recoverable_interview(recoverable)
                    st.rerun()
            with discard_col:
                if st.button(
                    "Discard saved interview",
                    type="secondary",
                    width="stretch",
                ):
                    try:
                        _database_service().abandon_interview(
                            interview_id=recoverable["id"]
                        )
                        st.session_state["_recoverable_interview"] = None
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    with st.container(border=True):
        ui_theme.render_section_heading(
            1,
            "Choose the interview focus",
            "Set the language, company context, and kind of interview you expect.",
        )
        focus_col1, focus_col2 = st.columns(2)
        languages = language_support.get_language_list()
        lang_options = {lang["display"]: lang["code"] for lang in languages}
        current_lang = st.session_state.get("selected_language", "en")

        with focus_col1:
            selected_lang_display = st.selectbox(
                get_ui_text("language"),
                options=list(lang_options.keys()),
                index=list(lang_options.values()).index(current_lang)
                if current_lang in lang_options.values()
                else 0,
                key="language_selector",
            )
        st.session_state["selected_language"] = lang_options[selected_lang_display]
        persistence.save_to_browser(
            "language",
            st.session_state["selected_language"],
            key="save_interface_language",
        )

        companies = company_prep.get_company_list()
        company_by_name = {company["name"]: company["key"] for company in companies}
        company_names = list(company_by_name)
        current_company = st.session_state.get("selected_company", "general")
        current_company_name = next(
            (
                company["name"]
                for company in companies
                if company["key"] == current_company
            ),
            company_names[0],
        )
        with focus_col2:
            selected_company_name = st.selectbox(
                "Company context",
                company_names,
                index=company_names.index(current_company_name),
                key="company_selector",
                help="Choose General if you are not targeting a specific company.",
            )
        st.session_state["selected_company"] = company_by_name[selected_company_name]
        company_info = company_prep.get_company_info(
            st.session_state["selected_company"]
        )

        with st.expander(f"{company_info['name']} interview guide", expanded=False):
            st.markdown(f"**Interview style:** {company_info['interview_style']}")
            guide_col1, guide_col2 = st.columns(2)
            with guide_col1:
                st.markdown("**Focus areas**")
                for area in company_info["focus_areas"]:
                    st.markdown(f"- {area}")
            with guide_col2:
                st.markdown("**Useful preparation**")
                for tip in company_info["tips"][:3]:
                    st.markdown(f"- {tip}")

        st.markdown(f"**{get_ui_text('select_interview_type')}**")
        type_cols = st.columns(5)
        for index, (type_name, type_info) in enumerate(INTERVIEW_TYPES.items()):
            with type_cols[index]:
                is_selected = st.session_state.get("interview_type") == type_name
                if st.button(
                    type_name,
                    key=f"type_{type_name}",
                    type="primary" if is_selected else "secondary",
                    help=type_info["description"],
                    width="stretch",
                ):
                    st.session_state["interview_type"] = type_name
                    st.rerun()

        selected_type = st.session_state.get("interview_type", "Mixed")
        type_info = INTERVIEW_TYPES[selected_type]
        st.caption(f"{selected_type}: {type_info['description']}")

    with st.container(border=True):
        ui_theme.render_section_heading(
            2,
            "Add the role context",
            "Your resume and the job description keep every question relevant.",
        )
        resume_col, job_col = st.columns(2, gap="large")

        with resume_col:
            st.markdown(f"#### {get_ui_text('upload_resume')}")
            resume_input_method = st.radio(
                "Resume input",
                ["Upload PDF", "Paste text"],
                horizontal=True,
                key="resume_input_method",
                label_visibility="collapsed",
            )

            if resume_input_method == "Upload PDF":
                resume_file = st.file_uploader(
                    "Upload your resume",
                    type=["pdf"],
                    key="interview_resume_upload",
                    help="HireSense uses the extracted text to personalize questions.",
                )
                if resume_file:
                    with st.spinner("Reading your resume..."):
                        resume_text = extract_uploaded_pdf(resume_file, "Resume")
                        if resume_text:
                            st.session_state["interview_resume_text"] = resume_text
                            st.session_state["_resume_upload_bytes"] = (
                                resume_file.getvalue()
                            )
                            st.session_state["_resume_upload_name"] = resume_file.name
                            st.success(f"Resume ready: {resume_file.name}")
                            persistence.save_to_browser(
                                "resume_text",
                                resume_text,
                                key="save_uploaded_resume",
                            )
                    if resume_text:
                        with st.expander("Preview extracted resume"):
                            st.text(
                                resume_text[:1000] + "..."
                                if len(resume_text) > 1000
                                else resume_text
                            )
                        if _database_session_ready():
                            st.session_state["save_resume_file"] = st.checkbox(
                                "Save the original PDF in private cloud storage",
                                value=bool(
                                    st.session_state.get("save_resume_file", False)
                                ),
                                help=(
                                    "Optional. Extracted text is saved for interview "
                                    "recovery, but the original file is stored only "
                                    "when this is selected."
                                ),
                            )
            else:
                pasted_resume = st.text_area(
                    "Resume text",
                    height=220,
                    key="interview_resume_text_input",
                    value=st.session_state.get("interview_resume_text") or "",
                    placeholder="Paste your resume content here...",
                )
                if pasted_resume:
                    st.session_state["interview_resume_text"] = pasted_resume
                    st.session_state["_resume_upload_bytes"] = None
                    st.session_state["_resume_upload_name"] = None
                    st.session_state["save_resume_file"] = False
                    persistence.save_to_browser(
                        "resume_text",
                        pasted_resume,
                        key="save_pasted_resume",
                    )

        with job_col:
            st.markdown(f"#### {get_ui_text('job_description')}")
            st.session_state["target_role"] = st.text_input(
                "Target role",
                value=st.session_state.get("target_role") or "",
                placeholder="For example: Machine Learning Engineer",
                help="This label appears in your saved interview history.",
            )
            jd_input_method = st.radio(
                "Job description input",
                ["Upload PDF", "Paste text"],
                horizontal=True,
                key="jd_input_method",
                label_visibility="collapsed",
            )

            if jd_input_method == "Upload PDF":
                jd_file = st.file_uploader(
                    "Upload the job description",
                    type=["pdf"],
                    key="interview_jd_upload",
                )
                if jd_file:
                    with st.spinner("Reading the job description..."):
                        jd_text = extract_uploaded_pdf(
                            jd_file,
                            "Job description",
                        )
                        if jd_text:
                            st.session_state["interview_jd_text"] = jd_text
                            st.success(f"Job description ready: {jd_file.name}")
                            persistence.save_to_browser(
                                "jd_text",
                                jd_text,
                                key="save_uploaded_jd",
                            )
            else:
                jd_text = st.text_area(
                    "Job description text",
                    height=220,
                    key="interview_jd_text_input",
                    value=st.session_state.get("interview_jd_text") or "",
                    placeholder="Paste the role responsibilities and requirements here...",
                )
                if jd_text:
                    st.session_state["interview_jd_text"] = jd_text
                    persistence.save_to_browser(
                        "jd_text",
                        jd_text,
                        key="save_pasted_jd",
                    )

        if st.session_state.get("interview_resume_text") and st.session_state.get(
            "interview_jd_text"
        ):
            with st.expander("Optional role-fit analysis", expanded=False):
                st.caption(
                    "Compare the explicit skills in your resume with the role before "
                    "starting the interview."
                )
                if not st.session_state.get("skill_analysis_done"):
                    if st.button("Analyze role fit", type="secondary"):
                        with st.spinner("Comparing role requirements and skills..."):
                            result = skill_gap_analysis.run_full_skill_analysis(
                                st.session_state["interview_resume_text"],
                                st.session_state["interview_jd_text"],
                            )
                            st.session_state["skill_analysis_result"] = result
                            st.session_state["skill_analysis_done"] = True
                            st.rerun()
                else:
                    result = st.session_state.get("skill_analysis_result", {})
                    stats = result.get("summary_stats", {})
                    if not result.get("available", False):
                        st.warning(
                            result.get("error")
                            or "Role-fit analysis is currently unavailable."
                        )
                    else:
                        score = stats.get("overall_score")
                        metric_cols = st.columns(4)
                        metric_cols[0].metric(
                            "Role match",
                            f"{score}%" if isinstance(score, (int, float)) else "N/A",
                        )
                        metric_cols[1].metric(
                            "Matching", stats.get("matching_count", 0)
                        )
                        metric_cols[2].metric("Gaps", stats.get("gap_count", 0))
                        metric_cols[3].metric(
                            "Additional", stats.get("exceeding_count", 0)
                        )

                        with st.expander("View full analysis"):
                            st.markdown(
                                result.get(
                                    "formatted_report",
                                    "No analysis available",
                                )
                            )
                            radar_data = result.get("radar_data", {})
                            if radar_data.get("categories"):
                                st.iframe(
                                    skill_gap_analysis.get_skill_gap_chart_html(
                                        radar_data
                                    ),
                                    height=350,
                                )
                    if st.button("Analyze again"):
                        st.session_state["skill_analysis_done"] = False
                        st.rerun()

    with st.container(border=True):
        ui_theme.render_section_heading(
            3,
            "Choose the interview experience",
            "Live voice feels conversational. Text mode gives you more time to compose.",
        )
        mode_options = ["📝 Text Interview", "🎙️ Live Voice Interview"]
        interview_mode = st.radio(
            "Interview format",
            mode_options,
            horizontal=True,
            key="interview_mode_selector",
            format_func=lambda value: (
                "Text interview"
                if value == "📝 Text Interview"
                else "Live voice interview"
            ),
        )
        st.session_state["interview_mode"] = interview_mode
        is_voice_mode = interview_mode == "🎙️ Live Voice Interview"

        if is_voice_mode:
            st.info(
                "HireSense speaks each question, captures an editable live transcript, "
                "and can ask one focused follow-up when important evidence is missing."
            )

        settings_col1, settings_col2 = st.columns(2)
        with settings_col1:
            num_questions = st.slider(
                get_ui_text("num_questions"),
                min_value=3,
                max_value=10,
                value=5,
                key="num_questions_slider",
            )
        st.session_state["total_questions"] = num_questions

        with settings_col2:
            st.session_state["followup_enabled"] = st.checkbox(
                "Allow one adaptive follow-up",
                value=True,
                help="HireSense asks for missing context, action, reasoning, or results.",
            )

        st.session_state["video_recording_enabled"] = False
        if is_voice_mode:
            st.session_state["tts_enabled"] = True
            st.session_state["voice_input_enabled"] = True
            with st.expander("Advanced practice options", expanded=False):
                st.session_state["webcam_enabled"] = st.checkbox(
                    "Use the optional facial practice signal",
                    value=False,
                    help=(
                        "Experimental and excluded from evidence scoring. Leave it "
                        "off for an answer-only interview."
                    ),
                )
        else:
            text_setting_col1, text_setting_col2, text_setting_col3 = st.columns(3)
            with text_setting_col1:
                st.session_state["tts_enabled"] = st.checkbox(
                    get_ui_text("enable_voice"),
                    value=True,
                    help="HireSense reads questions aloud.",
                )
            with text_setting_col2:
                st.session_state["voice_input_enabled"] = st.checkbox(
                    get_ui_text("enable_voice_input"),
                    value=True,
                    help="Speak an answer instead of typing it.",
                )
            with text_setting_col3:
                st.session_state["webcam_enabled"] = st.checkbox(
                    "Optional facial signal",
                    value=False,
                    help="Experimental and excluded from the evidence score.",
                )

    can_start = bool(
        st.session_state.get("interview_resume_text")
        and st.session_state.get("interview_jd_text")
    )
    with st.container(border=True):
        ui_theme.render_section_heading(
            4,
            "Review and begin",
            "HireSense will keep the assessment grounded in the transcript.",
        )
        summary_cols = st.columns(4)
        summary_cols[0].metric(
            "Format",
            "Live voice"
            if st.session_state.get("interview_mode")
            == "🎙️ Live Voice Interview"
            else "Text",
        )
        summary_cols[1].metric(
            "Focus", st.session_state.get("interview_type", "Mixed")
        )
        summary_cols[2].metric(
            "Questions", st.session_state.get("total_questions", 5)
        )
        summary_cols[3].metric("Company", company_info["name"])

    if not can_start:
        st.warning(
            "Add both your resume and the job description to unlock the interview."
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            get_ui_text("start_session"),
            type="primary",
            disabled=not can_start,
            width="stretch",
        ):
            # Build RAG context with company-specific info
            resume_data = arena.parse_resume(st.session_state["interview_resume_text"])
            jd_data = arena.parse_job_description(st.session_state["interview_jd_text"])
            base_context = arena.build_rag_context(resume_data, jd_data)

            # Add company-specific context
            company_prompt = company_prep.get_company_interview_prompt(
                st.session_state.get("selected_company", "general")
            )

            # Add language instruction
            lang_prompt = language_support.get_interview_language_prompt(
                st.session_state.get("selected_language", "en")
            )

            st.session_state["interview_rag_context"] = (
                f"{base_context}\n\n{company_prompt}\n\n{lang_prompt}"
            )

            # Reset interview state
            st.session_state["interview_started"] = True
            st.session_state["interview_history"] = []

            # Keep analysis/model caches scoped to this browser session.
            _cancel_question_prefetch()
            st.session_state["_interview_orchestrator"] = None
            st.session_state["_latency_session_id"] = uuid4().hex
            st.session_state["latency_samples"] = []
            st.session_state["interview_stress_timeline"] = []
            st.session_state["current_question_num"] = 1
            st.session_state["interview_complete"] = False
            st.session_state["interview_start_time"] = time.time()
            st.session_state["awaiting_question"] = True
            st.session_state["interview_report"] = None
            st.session_state["evidence_assessment"] = None
            st.session_state["evidence_assessment_error"] = None
            st.session_state["current_stress_level"] = None
            st.session_state["emotion_reading"] = None
            st.session_state["manual_stress_override"] = None
            st.session_state["current_question_text"] = None
            st.session_state["current_question_source"] = None
            st.session_state["current_question_status"] = None
            st.session_state["current_question_is_followup"] = False
            st.session_state["current_question_revision"] = 0
            st.session_state["last_followup_decision"] = None
            st.session_state["rephrase_notice"] = None
            st.session_state["tts_played"] = False
            st.session_state["current_voice_answer"] = ""
            st.session_state["followup_count"] = 0
            st.session_state["awaiting_followup"] = False
            st.session_state["_database_completion_queued_for"] = None

            interview_id = str(uuid4())
            st.session_state["active_interview_id"] = interview_id
            _start_database_interview(interview_id)

            if (
                st.session_state.get("interview_mode")
                == "🎙️ Live Voice Interview"
            ):
                _schedule_next_base_question(target_question=1)

            # Initialize video recording if enabled
            if st.session_state.get("video_recording_enabled"):
                video_recording.start_recording_session()

            st.rerun()


def _enforce_live_voice_product_defaults() -> None:
    """Keep the public product on one predictable live voice path."""
    facial_signal_consent = bool(
        st.session_state.get("facial_signal_consent", False)
    )
    st.session_state.update(
        {
            "page": "interview",
            "interview_mode": LIVE_VOICE_MODE,
            "interview_type": "Mixed",
            "selected_company": "general",
            "total_questions": LIVE_VOICE_QUESTION_COUNT,
            "followup_enabled": True,
            "max_followups": 1,
            "max_total_followups": interview_flow.MAX_TOTAL_FOLLOWUPS,
            "tts_enabled": True,
            "voice_input_enabled": True,
            "webcam_enabled": facial_signal_consent,
            "video_recording_enabled": False,
            "copilot_enabled": False,
            "coding_mode_enabled": False,
            "save_resume_file": True,
        }
    )


def _begin_live_voice_interview() -> None:
    """Prepare one personalized live voice interview with safe fixed defaults."""
    _enforce_live_voice_product_defaults()
    resume_text = str(st.session_state.get("interview_resume_text") or "").strip()
    job_description = str(
        st.session_state.get("interview_jd_text") or ""
    ).strip()
    if not resume_text or not job_description:
        raise ValueError("A resume and job description are required.")

    resume_data = arena.parse_resume(resume_text)
    jd_data = arena.parse_job_description(job_description)
    base_context = arena.build_rag_context(resume_data, jd_data)
    language_prompt = language_support.get_interview_language_prompt(
        st.session_state.get("selected_language", "en")
    )
    st.session_state["interview_rag_context"] = (
        f"{base_context}\n\n{language_prompt}"
    )
    if not str(st.session_state.get("target_role") or "").strip():
        st.session_state["target_role"] = "Role-specific practice"

    _cancel_question_prefetch()
    st.session_state.update(
        {
            "interview_started": True,
            "interview_history": [],
            "_interview_orchestrator": None,
            "_latency_session_id": uuid4().hex,
            "latency_samples": [],
            "interview_stress_timeline": [],
            "facial_support_questions": [],
            "current_question_num": 1,
            "interview_complete": False,
            "interview_start_time": time.time(),
            "awaiting_question": True,
            "interview_report": None,
            "evidence_assessment": None,
            "evidence_assessment_error": None,
            "current_stress_level": None,
            "emotion_reading": None,
            "manual_stress_override": None,
            "current_question_text": None,
            "current_question_source": None,
            "current_question_status": None,
            "current_question_is_followup": False,
            "current_question_revision": 0,
            "last_followup_decision": None,
            "rephrase_notice": None,
            "tts_played": False,
            "current_voice_answer": "",
            "followup_count": 0,
            "total_followups_asked": 0,
            "awaiting_followup": False,
            "_database_completion_queued_for": None,
        }
    )

    interview_id = str(uuid4())
    st.session_state["active_interview_id"] = interview_id
    _start_database_interview(interview_id)


def render_interview_setup() -> None:
    """Render the single-path setup for nontechnical candidates."""
    _enforce_live_voice_product_defaults()
    ui_theme.render_page_header(
        "Live Voice Interview",
        "Practise your next interview out loud",
        (
            "Upload your resume and paste the job description. HireSense handles "
            "the interview flow, starts with the basics, and gradually increases "
            "the difficulty."
        ),
    )

    if _database_session_ready() and st.session_state.get(
        "_database_sync_error"
    ):
        st.warning(
            "Your interview is still available, but cloud saving is temporarily "
            "unavailable."
        )

    recoverable = st.session_state.get("_recoverable_interview")
    if isinstance(recoverable, dict) and recoverable.get("id"):
        with st.container(border=True):
            st.markdown("### Continue where you stopped")
            st.caption(
                f"{recoverable.get('target_role', 'Practice interview')} · "
                f"{recoverable.get('turn_count', 0)} answers saved"
            )
            resume_col, discard_col = st.columns(2)
            with resume_col:
                if st.button(
                    "Continue interview",
                    type="primary",
                    width="stretch",
                ):
                    _resume_recoverable_interview(recoverable)
                    _enforce_live_voice_product_defaults()
                    st.rerun()
            with discard_col:
                if st.button(
                    "Start fresh",
                    type="secondary",
                    width="stretch",
                ):
                    try:
                        _database_service().abandon_interview(
                            interview_id=recoverable["id"]
                        )
                        st.session_state["_recoverable_interview"] = None
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    with st.container(border=True):
        st.markdown("### Get ready")
        st.caption(
            "You only need two things. HireSense chooses the interview format, "
            "focus, and number of questions automatically."
        )
        resume_col, job_col = st.columns(2, gap="large")

        with resume_col:
            st.markdown("#### 1. Upload your resume")
            resume_file = st.file_uploader(
                "Resume PDF",
                type=["pdf"],
                key="live_voice_resume_upload",
                help="Upload the resume you will use for this job application.",
            )
            if resume_file:
                uploaded_bytes = resume_file.getvalue()
                if uploaded_bytes != st.session_state.get("_resume_upload_bytes"):
                    with st.spinner("Reading your resume..."):
                        resume_text = extract_uploaded_pdf(resume_file, "Resume")
                    if resume_text:
                        st.session_state["interview_resume_text"] = resume_text
                        st.session_state["_resume_upload_bytes"] = uploaded_bytes
                        st.session_state["_resume_upload_name"] = resume_file.name
                        st.session_state["save_resume_file"] = True
                        st.session_state["resume_saved_to_supabase"] = False
                        st.session_state["resume_storage_status"] = None
                        persistence.save_to_browser(
                            "resume_text",
                            resume_text,
                            key="save_live_voice_resume",
                        )
            if st.session_state.get("interview_resume_text"):
                resume_name = st.session_state.get("_resume_upload_name")
                st.success(
                    f"Resume ready: {resume_name}"
                    if resume_name
                    else "Your saved resume is ready."
                )
                st.caption(
                    "Your extracted resume and original PDF will be saved "
                    "privately to your account when the interview starts."
                )

        with job_col:
            st.markdown("#### 2. Add the job description")
            job_description = st.text_area(
                "Paste the job description",
                height=220,
                value=st.session_state.get("interview_jd_text") or "",
                key="live_voice_job_description",
                placeholder=(
                    "Copy the responsibilities and requirements from the job post "
                    "and paste them here."
                ),
            )
            normalized_job_description = job_description.strip()
            st.session_state["interview_jd_text"] = (
                normalized_job_description or None
            )
            persistence.save_to_browser(
                "jd_text",
                normalized_job_description,
                key="save_live_voice_job_description",
            )
            if normalized_job_description:
                st.success("Job description ready.")

        with st.expander("Optional: role name or interview language"):
            detail_col, language_col = st.columns(2)
            with detail_col:
                st.session_state["target_role"] = st.text_input(
                    "Role name",
                    value=st.session_state.get("target_role") or "",
                    placeholder="For example: Machine Learning Engineer",
                ).strip()

            languages = language_support.get_language_list()
            language_options = {
                language["display"]: language["code"] for language in languages
            }
            current_language = st.session_state.get("selected_language", "en")
            current_display = next(
                (
                    display
                    for display, code in language_options.items()
                    if code == current_language
                ),
                next(iter(language_options)),
            )
            with language_col:
                selected_language = st.selectbox(
                    "Interview language",
                    options=list(language_options),
                    index=list(language_options).index(current_display),
                    key="live_voice_language_selector",
                )
            st.session_state["selected_language"] = language_options[
                selected_language
            ]
            persistence.save_to_browser(
                "language",
                st.session_state["selected_language"],
                key="save_live_voice_language",
            )

    with st.container(border=True):
        st.markdown("### Optional camera coaching")
        st.session_state["facial_signal_consent"] = st.checkbox(
            "Use my Viva Defense facial-expression model",
            key="live_voice_facial_signal_consent",
            value=bool(
                st.session_state.get("facial_signal_consent", False)
            ),
            help=(
                "The camera feed and model run in your browser. HireSense records "
                "only one numeric expression checkpoint after each answer."
            ),
        )
        st.session_state["webcam_enabled"] = st.session_state[
            "facial_signal_consent"
        ]
        st.caption(
            "Frames stay on your device and are not recorded or uploaded. "
            "The signal may soften Maya's wording after repeated stressed-like "
            "expressions, but it never changes your question difficulty or score."
        )

        if st.session_state["facial_signal_consent"]:
            with st.expander("Check camera and Viva Defense model", expanded=True):
                emotion_reading = webcam.render_webcam_emotion_detector(
                    key="setup_viva_defense_detector",
                    default=st.session_state.get("emotion_reading"),
                )
                st.session_state["emotion_reading"] = emotion_reading
                if webcam.reading_is_usable(emotion_reading):
                    st.success("Camera and Viva Defense model are ready.")
                elif emotion_reading.get("status") == "error":
                    st.warning(
                        "Camera coaching is unavailable. You can still complete "
                        "the live voice interview."
                    )

    can_start = bool(
        st.session_state.get("interview_resume_text")
        and st.session_state.get("interview_jd_text")
    )
    st.caption(
        "Natural interview stages · Adaptive follow-ups · Gradually increasing "
        "difficulty · Transcript and optional camera coaching"
    )
    if not can_start:
        st.info(
            "Upload your resume and paste the job description to start the interview."
        )

    button_col1, button_col2, button_col3 = st.columns([1, 2, 1])
    with button_col2:
        if st.button(
            "Start live voice interview",
            type="primary",
            disabled=not can_start,
            width="stretch",
        ):
            with st.spinner("Preparing your interview..."):
                _begin_live_voice_interview()
            st.rerun()


def render_live_voice_session():
    """Render a low-latency, adaptive live voice interview."""
    import live_voice_interview as lvi

    ui_theme.enable_focus_mode()
    interview_type = st.session_state.get("interview_type", "Mixed")
    language_info = language_support.get_language_info(
        st.session_state.get("selected_language", "en")
    )
    ui_theme.render_voice_only_header(
        language=language_info.get("name", "English"),
        question_number=st.session_state.get("current_question_num", 1),
        total_questions=st.session_state.get("total_questions", 1),
    )
    if (
        st.session_state.get("resume_storage_status") == "text_saved"
        and st.session_state.get("_database_sync_error")
    ):
        st.warning(
            "Your resume text is saved privately, but the original PDF could not "
            "be stored. You can continue this practice interview."
        )

    if st.session_state.get("webcam_enabled", False):
        with st.expander("Viva Defense camera coaching", expanded=False):
            emotion_reading = webcam.render_webcam_emotion_detector(
                key="live_voice_emotion_detector",
                default=st.session_state.get("emotion_reading"),
            )
            st.session_state["emotion_reading"] = emotion_reading
            if webcam.reading_is_usable(emotion_reading):
                st.session_state["current_stress_level"] = emotion_reading[
                    "stress_score"
                ]
            else:
                st.session_state["current_stress_level"] = None
            st.caption(
                "Frames stay on this device and are never recorded. The model "
                "estimates confident-like versus stressed-like expressions; it "
                "does not know how confident you actually feel."
            )

    if st.session_state.get("interview_complete"):
        render_interview_results()
        return

    if st.session_state.get("awaiting_followup", False):
        with st.spinner("HireSense is preparing a targeted follow-up..."):
            st.session_state["current_emotional_state"] = (
                _facial_interviewer_state(
                    st.session_state.get("current_question_num", 1)
                )
            )
            history = st.session_state["interview_history"]
            if len(history) >= 2:
                original_question = history[-2]["content"]
                candidate_answer = history[-1]["content"]
                decision = st.session_state.get("last_followup_decision") or {}
                followup_gen = followup_questions.generate_smart_followup(
                    original_question=original_question,
                    candidate_answer=candidate_answer,
                    rag_context=st.session_state.get("interview_rag_context", ""),
                    interview_type=interview_type,
                    emotional_state=st.session_state.get(
                        "current_emotional_state", "neutral"
                    ),
                    language=st.session_state.get("selected_language", "en"),
                    followup_type=decision.get("suggested_type"),
                    missing_element=decision.get("missing_element", ""),
                )
                generated = latency_optimizer.foreground_question(followup_gen)
                question_text = generated.text
                question_status = generated.status
            else:
                question_text = ""
                question_status = {
                    "source": "built_in_fallback",
                    "reason": "missing_previous_exchange",
                    "delivery": "foreground",
                    "generation_ms": 0,
                    "prefetch_wait_ms": 0,
                }

            if not question_text:
                question_text = (
                    "Could you give one specific detail that makes your answer "
                    "more concrete?"
                )
                question_status = {
                    "source": "built_in_fallback",
                    "reason": "empty_followup",
                    "delivery": "foreground",
                    "generation_ms": question_status.get("generation_ms", 0),
                    "prefetch_wait_ms": 0,
                }

            st.session_state["interview_history"].append(
                {
                    "role": "assistant",
                    "content": question_text,
                    "timestamp": time.time(),
                    "is_followup": True,
                    "followup_focus": (
                        st.session_state.get("last_followup_decision") or {}
                    ).get("missing_element"),
                    "generation_source": question_status.get("source", "model"),
                }
            )
            st.session_state["current_question_text"] = question_text
            st.session_state["current_question_source"] = question_status.get(
                "source", "model"
            )
            st.session_state["current_question_status"] = question_status
            st.session_state["current_question_is_followup"] = True
            st.session_state["awaiting_followup"] = False
            st.session_state["followup_count"] = (
                st.session_state.get("followup_count", 0) + 1
            )
            st.session_state["total_followups_asked"] = (
                st.session_state.get("total_followups_asked", 0) + 1
            )
            st.session_state["current_question_revision"] = (
                st.session_state.get("current_question_revision", 0) + 1
            )
            _record_question_latency(
                question_number=st.session_state["current_question_num"],
                is_followup=True,
                status=question_status,
            )

    elif st.session_state.get("awaiting_question", True):
        with st.spinner("HireSense is preparing your next question..."):
            question_number = st.session_state["current_question_num"]
            # Facial coaching can soften wording after repeated stressed-like
            # checkpoints. The planned phase and difficulty remain unchanged.
            st.session_state["current_emotional_state"] = (
                _facial_interviewer_state(question_number)
            )
            prefetched = _resolve_prefetched_base_question(question_number)

            if (
                prefetched.state == "hit"
                and prefetched.question is not None
                and prefetched.question.text
            ):
                question_text = prefetched.question.text
                question_status = prefetched.question.status
            elif prefetched.state in {"timeout", "error"}:
                question_text = arena.get_builtin_interview_question(
                    interview_type,
                    question_number,
                    st.session_state["total_questions"],
                )
                question_status = {
                    "source": "built_in_fallback",
                    "reason": prefetched.reason or prefetched.state,
                    "delivery": "latency_fallback",
                    "generation_ms": None,
                    "prefetch_wait_ms": prefetched.wait_ms,
                }
            else:
                orchestrator = (
                    _get_interview_orchestrator() if CONFIG_IS_VALID else None
                )
                question_gen = arena.generate_interview_question(
                    st.session_state["interview_rag_context"],
                    st.session_state["interview_history"],
                    st.session_state["current_emotional_state"],
                    question_number,
                    st.session_state["total_questions"],
                    interview_type,
                    company=st.session_state.get("selected_company", "general"),
                    orchestrator=orchestrator,
                )
                generated = latency_optimizer.foreground_question(question_gen)
                question_text = generated.text
                question_status = generated.status

            if not question_text:
                question_text = arena.get_builtin_interview_question(
                    interview_type,
                    question_number,
                    st.session_state["total_questions"],
                )
                question_status = {
                    "source": "built_in_fallback",
                    "reason": "empty_question",
                    "delivery": question_status.get("delivery", "foreground"),
                    "generation_ms": question_status.get("generation_ms"),
                    "prefetch_wait_ms": question_status.get("prefetch_wait_ms", 0),
                }

            st.session_state["interview_history"].append(
                {
                    "role": "assistant",
                    "content": question_text,
                    "timestamp": time.time(),
                    "is_followup": False,
                    "generation_source": question_status.get("source", "model"),
                    "phase": interview_flow.phase_for_question(
                        question_number,
                        st.session_state["total_questions"],
                    ).key,
                }
            )
            st.session_state["current_question_text"] = question_text
            st.session_state["current_question_source"] = question_status.get(
                "source", "model"
            )
            st.session_state["current_question_status"] = question_status
            st.session_state["current_question_is_followup"] = False
            st.session_state["awaiting_question"] = False
            st.session_state["followup_count"] = 0
            st.session_state["current_question_revision"] = (
                st.session_state.get("current_question_revision", 0) + 1
            )
            _record_question_latency(
                question_number=question_number,
                is_followup=False,
                status=question_status,
            )

    question_text = st.session_state.get("current_question_text", "")
    if question_text:
        is_followup = st.session_state.get("current_question_is_followup", False)
        current_phase = interview_flow.phase_for_question(
            st.session_state["current_question_num"],
            st.session_state["total_questions"],
        )
        visible_label = (
            f"{current_phase.name} follow-up"
            if is_followup
            else current_phase.name
        )
        rephrase_notice = st.session_state.get("rephrase_notice")
        if rephrase_notice:
            if "unavailable" in rephrase_notice.casefold():
                st.warning(rephrase_notice)
            else:
                st.success(rephrase_notice)

        if st.session_state.get("current_question_source") == "built_in_fallback":
            st.warning(
                "Personalized question generation was unavailable. HireSense is "
                "using a disclosed built-in question so the interview can continue."
            )
            if st.button("Retry personalized question", key="retry_live_ai_question"):
                retry_current_question()
                st.rerun()

        speech_lang = language_support.get_speech_recognition_code(
            st.session_state.get("selected_language", "en")
        )
        voice_result = lvi.render_live_voice_component(
            question_text=question_text,
            question_num=st.session_state["current_question_num"],
            total_questions=st.session_state["total_questions"],
            language_code=speech_lang,
            language_label=language_info.get("name", speech_lang),
            tts_speed=1.0,
            question_revision=st.session_state.get("current_question_revision", 0),
            question_label=visible_label,
            support_mode=(
                st.session_state.get("current_emotional_state")
                == "stress_signal"
            ),
        )

        if voice_result:
            submission_id = voice_result["submission_id"]
            if submission_id != st.session_state.get("_last_live_voice_submission"):
                st.session_state["_last_live_voice_submission"] = submission_id
                if _handle_live_voice_control_action(voice_result["action"]):
                    return

                answer_text = voice_result["answer"]
                latency = voice_result.get("latency") or {}
                speech_stats = {
                    "word_count": voice_result["word_count"],
                    "hesitations": voice_result["hesitations"],
                    "latency": latency,
                    "capture_ms": latency.get("capture_ms"),
                    "recognition_confidence": voice_result.get(
                        "recognition_confidence"
                    ),
                    "response_start_ms": voice_result.get("response_start_ms"),
                    "speaking_duration_ms": voice_result.get(
                        "speaking_duration_ms"
                    ),
                    "pause_count": voice_result.get("pause_count"),
                    "pause_ms": voice_result.get("pause_ms"),
                    "manual_submit": voice_result.get("manual_submit"),
                }
                delivery_signal = confidence_model.estimate_delivery_confidence(
                    answer_text,
                    speech_stats,
                )
                speech_stats["delivery_confidence"] = delivery_signal
                record_current_stress(st.session_state["current_question_num"])
                _record_client_latency(
                    question_number=st.session_state["current_question_num"],
                    latency=voice_result.get("latency"),
                )
                st.session_state["interview_history"].append(
                    {
                        "role": "user",
                        "content": answer_text,
                        "timestamp": time.time(),
                        "speech_stats": speech_stats,
                    }
                )
                _persist_confirmed_turn(
                    answer_text,
                    is_followup=is_followup,
                    transcription_engine="browser_speech",
                    speech_stats=speech_stats,
                )
                _advance_after_answer(
                    answer_text,
                    answered_followup=is_followup,
                )
                st.rerun()

    if st.button("End interview", width="stretch"):
        st.session_state["interview_complete"] = True
        _cancel_question_prefetch()
        save_to_question_bank()
        st.rerun()

    # Show conversation history
    if st.session_state["interview_history"]:
        with st.expander("Conversation history", expanded=False):
            for entry in st.session_state["interview_history"]:
                role = "Interviewer" if entry["role"] == "assistant" else "You"
                followup = " (follow-up)" if entry.get("is_followup") else ""
                st.markdown(
                    f"**{role}{followup}:** {entry['content'][:300]}..."
                    if len(entry["content"]) > 300
                    else f"**{role}{followup}:** {entry['content']}"
                )

    if config.developer_controls_enabled() and st.session_state.get(
        "latency_samples"
    ):
        with st.expander("Latency diagnostics", expanded=False):
            samples = st.session_state["latency_samples"]
            generation = [
                sample
                for sample in samples
                if sample.get("generation_ms") is not None
            ]
            voice_capture = [
                sample for sample in samples if sample.get("phase") == "voice_capture"
            ]
            metric_columns = st.columns(3)
            metric_columns[0].metric(
                "Latest question generation",
                (
                    f"{generation[-1]['generation_ms']} ms"
                    if generation
                    else "N/A"
                ),
            )
            metric_columns[1].metric(
                "Latest hand-off wait",
                (
                    f"{generation[-1].get('prefetch_wait_ms', 0)} ms"
                    if generation
                    else "N/A"
                ),
            )
            metric_columns[2].metric(
                "Latest end-of-speech",
                (
                    f"{voice_capture[-1].get('end_of_speech_ms')} ms"
                    if voice_capture
                    and voice_capture[-1].get("end_of_speech_ms") is not None
                    else "N/A"
                ),
            )
            st.caption(
                "Diagnostics contain timing values only, not resume or transcript text."
            )


def render_active_interview():
    """Render the active HireSense AI interview interface."""
    ui_theme.enable_focus_mode()
    interview_type = st.session_state.get("interview_type", "Mixed")
    company_info = company_prep.get_company_info(
        st.session_state.get("selected_company", "general")
    )
    language_name = language_support.get_language_info(
        st.session_state.get("selected_language", "en")
    )["name"]
    ui_theme.render_live_header(
        interview_type=interview_type,
        company=company_info["name"],
        language=language_name,
        mode="Text interview",
        question_number=st.session_state.get("current_question_num", 1),
        total_questions=st.session_state.get("total_questions", 1),
    )

    progress = (
        st.session_state["current_question_num"] / st.session_state["total_questions"]
    )
    st.progress(
        progress,
        text=f"Question {st.session_state['current_question_num']} of {st.session_state['total_questions']}",
    )

    # Main interview layout
    col1, col2 = st.columns([3, 1])

    with col2:
        with st.container(border=True):
            st.markdown("#### Session")
            answered_count = len(
                [
                    item
                    for item in st.session_state["interview_history"]
                    if item.get("role") == "user"
                ]
            )
            st.metric("Answers captured", answered_count)
            if st.session_state["interview_start_time"]:
                elapsed = time.time() - st.session_state["interview_start_time"]
                st.metric("Elapsed time", f"{int(elapsed // 60)}m {int(elapsed % 60)}s")
            if st.session_state.get("followup_enabled"):
                st.metric("Follow-ups", st.session_state.get("followup_count", 0))

        if st.session_state.get("video_recording_enabled"):
            with st.expander("Video recording", expanded=True):
                video_recording.render_video_recorder(
                    height=400,
                    session_id=st.session_state.get("recording_session_id", "default"),
                )

        if st.session_state["webcam_enabled"] and not st.session_state.get(
            "video_recording_enabled"
        ):
            with st.expander("Optional facial practice signal", expanded=False):
                emotion_reading = webcam.render_webcam_emotion_detector(
                    key="active_interview_emotion_detector",
                    default=st.session_state.get("emotion_reading"),
                )
                st.session_state["emotion_reading"] = emotion_reading
                if webcam.reading_is_usable(emotion_reading):
                    st.session_state["current_stress_level"] = emotion_reading[
                        "stress_score"
                    ]
                    st.metric(
                        "Experimental stress signal",
                        f"{st.session_state['current_stress_level']:.0%}",
                    )
                else:
                    st.session_state["current_stress_level"] = None
                    st.caption("Reading unavailable. No substitute value is recorded.")

        if config.developer_controls_enabled():
            with st.expander("Developer stress override", expanded=False):
                use_override = st.checkbox(
                    "Use a simulated score",
                    value=st.session_state.get("manual_stress_override") is not None,
                    help="Development only. Simulated scores are labelled in exports.",
                )
                if use_override:
                    override_value = st.session_state.get("manual_stress_override")
                    if override_value is None:
                        override_value = st.session_state.get("current_stress_level")
                    if override_value is None:
                        override_value = 0.5
                    manual_stress = st.slider(
                        "Simulated stress score:",
                        0.0,
                        1.0,
                        float(override_value),
                        key="manual_stress_slider",
                    )
                    st.session_state["manual_stress_override"] = manual_stress
                    st.session_state["current_stress_level"] = manual_stress
                else:
                    st.session_state["manual_stress_override"] = None

    with col1:
        # Conversation display
        st.markdown("#### Interview conversation")

        # Display conversation history
        conversation_container = st.container()
        with conversation_container:
            for entry in st.session_state["interview_history"]:
                if entry["role"] == "assistant":
                    st.markdown(f"**HireSense:** {entry['content']}")
                else:
                    st.markdown(f"**You:** {entry['content']}")
                st.markdown("---")

        rephrase_notice = st.session_state.get("rephrase_notice")
        if rephrase_notice:
            if "unavailable" in rephrase_notice.casefold():
                st.warning(rephrase_notice)
            else:
                st.success(rephrase_notice)

        if (
            st.session_state.get("current_question_source") == "built_in_fallback"
            and st.session_state.get("current_question_text")
            and not st.session_state.get("awaiting_question", True)
        ):
            st.warning(
                "AI question generation was unavailable. The current question is "
                "a built-in backup question, not a personalized model response."
            )
            if st.button("Retry personalized question", key="retry_text_ai_question"):
                retry_current_question()
                st.rerun()

        # Generate question if needed
        should_generate = (
            st.session_state["awaiting_question"]
            and st.session_state["current_question_num"]
            <= st.session_state["total_questions"]
            and not st.session_state.get("awaiting_followup", False)
        )

        if should_generate:
            with st.spinner("🤔 HireSense AI is preparing the next question..."):
                # Keep question selection independent of appearance signals.
                st.session_state["current_emotional_state"] = "neutral"

                # Generate question with interview type
                question_gen = arena.generate_interview_question(
                    st.session_state["interview_rag_context"],
                    st.session_state["interview_history"],
                    st.session_state["current_emotional_state"],
                    st.session_state["current_question_num"],
                    st.session_state["total_questions"],
                    st.session_state.get("interview_type", "Mixed"),
                    company=st.session_state.get("selected_company", "general"),
                    orchestrator=(
                        _get_interview_orchestrator()
                        if CONFIG_IS_VALID
                        else None
                    ),
                )

                st.markdown("**HireSense:**")
                question_status = {}
                question_text = display_streaming_response(
                    question_gen, status_sink=question_status
                ).strip()
                if not question_text:
                    question_text = arena.get_builtin_interview_question(
                        st.session_state.get("interview_type", "Mixed"),
                        st.session_state["current_question_num"],
                    )
                    question_status = {
                        "source": "built_in_fallback",
                        "reason": "empty_question",
                    }

                # Add to history
                st.session_state["interview_history"].append(
                    {
                        "role": "assistant",
                        "content": question_text,
                        "timestamp": time.time(),
                        "is_followup": False,
                        "generation_source": question_status.get("source", "model"),
                    }
                )

                # Add video marker for question
                if st.session_state.get("video_recording_enabled"):
                    st.iframe(
                        video_recording.add_question_marker_js(
                            st.session_state["current_question_num"]
                        ),
                        height=0,
                    )

                st.session_state["current_question_text"] = question_text
                st.session_state["current_question_source"] = question_status.get(
                    "source", "model"
                )
                st.session_state["current_question_status"] = question_status
                st.session_state["current_question_is_followup"] = False
                st.session_state["current_question_revision"] = (
                    st.session_state.get("current_question_revision", 0) + 1
                )
                st.session_state["tts_played"] = False
                st.session_state["awaiting_question"] = False
                st.session_state["followup_count"] = 0

                st.rerun()

        # Generate follow-up question if needed (NEW)
        if st.session_state.get("awaiting_followup", False):
            with st.spinner("🤔 HireSense AI is preparing a follow-up question..."):
                # Get the last Q&A pair
                history = st.session_state["interview_history"]
                if len(history) >= 2:
                    last_question = history[-2]["content"]
                    last_answer = history[-1]["content"]

                    followup_gen = followup_questions.generate_smart_followup(
                        original_question=last_question,
                        candidate_answer=last_answer,
                        rag_context=st.session_state.get("interview_rag_context", ""),
                        interview_type=st.session_state.get("interview_type", "Mixed"),
                        emotional_state=st.session_state.get(
                            "current_emotional_state", "neutral"
                        ),
                        language=st.session_state.get("selected_language", "en"),
                        followup_type=(
                            st.session_state.get("last_followup_decision") or {}
                        ).get("suggested_type"),
                        missing_element=(
                            st.session_state.get("last_followup_decision") or {}
                        ).get("missing_element", ""),
                    )

                    st.markdown("**HireSense follow-up:**")
                    followup_status = {}
                    followup_text = display_streaming_response(
                        followup_gen, status_sink=followup_status
                    ).strip()

                    st.session_state["interview_history"].append(
                        {
                            "role": "assistant",
                            "content": followup_text,
                            "timestamp": time.time(),
                            "is_followup": True,
                            "generation_source": followup_status.get(
                                "source", "model"
                            ),
                        }
                    )

                    st.session_state["current_question_text"] = followup_text
                    st.session_state["current_question_source"] = (
                        followup_status.get("source", "model")
                    )
                    st.session_state["current_question_status"] = followup_status
                    st.session_state["current_question_is_followup"] = True
                    st.session_state["current_question_revision"] = (
                        st.session_state.get("current_question_revision", 0) + 1
                    )
                    st.session_state["tts_played"] = False
                    st.session_state["awaiting_followup"] = False
                    st.session_state["followup_count"] += 1

                    st.rerun()

        # Answer input
        if not st.session_state["awaiting_question"] and not st.session_state.get(
            "awaiting_followup", False
        ):
            st.markdown(f"#### {get_ui_text('your_response')}")

            answer_key = (
                f"answer_{st.session_state['current_question_num']}_"
                f"{st.session_state.get('followup_count', 0)}"
            )
            if answer_key not in st.session_state:
                st.session_state[answer_key] = ""

            # Browser voice I/O. Audio starts from an explicit browser click so
            # autoplay policies cannot silently swallow the interview question.
            if st.session_state.get("voice_input_enabled", True):
                with st.expander(get_ui_text("speak_your_answer"), expanded=True):
                    # Get speech recognition language code
                    speech_lang = language_support.get_speech_recognition_code(
                        st.session_state.get("selected_language", "en")
                    )
                    language_name = language_support.get_language_info(
                        st.session_state.get("selected_language", "en")
                    ).get("name", speech_lang)
                    component_key = "interview_voice_io"
                    voice_result = voice_input.render_voice_input(
                        key=component_key,
                        mode="standard",
                        language_code=speech_lang,
                        question_text=st.session_state.get(
                            "current_question_text", ""
                        ),
                        question_num=st.session_state["current_question_num"],
                        total_questions=st.session_state["total_questions"],
                        question_revision=st.session_state.get(
                            "current_question_revision", 0
                        ),
                        question_label=(
                            "Follow-up question"
                            if st.session_state.get("current_question_is_followup")
                            else "Interview question"
                        ),
                        language_label=language_name,
                        tts_speed=1.1,
                        tts_enabled=st.session_state.get("tts_enabled", True),
                    )
                    if voice_result and voice_result[
                        "submission_id"
                    ] != st.session_state.get(f"_last_{component_key}"):
                        st.session_state[f"_last_{component_key}"] = voice_result[
                            "submission_id"
                        ]
                        if voice_result["action"] == "rephrase":
                            _rephrase_current_question()
                            st.rerun()
                        elif voice_result["action"] == "answer":
                            st.session_state[answer_key] = voice_result["answer"]
                            st.session_state[f"{answer_key}_source"] = (
                                "browser_speech"
                            )
                    st.caption(
                        f"💡 Hear the question, answer by voice, then click "
                        f"'{get_ui_text('use_this_answer')}' to fill the text box below."
                    )
            elif st.session_state.get("tts_enabled", True):
                speech_lang = language_support.get_speech_recognition_code(
                    st.session_state.get("selected_language", "en")
                )
                voice_input.render_voice_input(
                    key="interview_question_speaker",
                    mode="speaker",
                    language_code=speech_lang,
                    question_text=st.session_state.get("current_question_text", ""),
                    question_num=st.session_state["current_question_num"],
                    total_questions=st.session_state["total_questions"],
                    tts_speed=1.1,
                    tts_enabled=True,
                )

            # Text input
            user_answer = st.text_area(
                "Your answer:",
                height=150,
                key=answer_key,
                placeholder="Type your answer here, or use voice input above...",
            )

            col_submit, col_followup, col_skip, col_end = st.columns(4)

            with col_submit:
                if st.button(
                    f"📤 {get_ui_text('submit_answer')}",
                    type="primary",
                    disabled=not user_answer,
                ):
                    record_current_stress(st.session_state["current_question_num"])

                    # Add answer to history
                    st.session_state["interview_history"].append(
                        {
                            "role": "user",
                            "content": user_answer,
                            "timestamp": time.time(),
                        }
                    )
                    answered_followup = st.session_state.get(
                        "current_question_is_followup",
                        False,
                    )
                    _persist_confirmed_turn(
                        user_answer,
                        is_followup=answered_followup,
                        transcription_engine=st.session_state.get(
                            f"{answer_key}_source",
                            "typed",
                        ),
                    )

                    _advance_after_answer(
                        user_answer,
                        answered_followup=answered_followup,
                    )

                    st.rerun()

            with col_followup:
                # Manual follow-up request (NEW)
                if (
                    st.session_state.get("followup_enabled")
                    and st.session_state.get("followup_count", 0)
                    < st.session_state.get("max_followups", 1)
                    and not st.session_state.get("current_question_is_followup", False)
                ):
                    if st.button("Ask a follow-up", disabled=not user_answer):
                        record_current_stress(st.session_state["current_question_num"])

                        st.session_state["interview_history"].append(
                            {
                                "role": "user",
                                "content": user_answer,
                                "timestamp": time.time(),
                            }
                        )
                        _persist_confirmed_turn(
                            user_answer,
                            is_followup=False,
                            transcription_engine=st.session_state.get(
                                f"{answer_key}_source",
                                "typed",
                            ),
                        )

                        decision = _followup_decision(
                            st.session_state.get("current_question_text", ""),
                            user_answer,
                        )
                        if not decision.get("should_followup"):
                            decision = {
                                "should_followup": True,
                                "reason": "Candidate requested a follow-up",
                                "suggested_type": "depth",
                                "missing_element": (
                                    "one additional role-relevant detail"
                                ),
                            }
                        st.session_state["last_followup_decision"] = decision
                        st.session_state["awaiting_followup"] = True
                        st.session_state["awaiting_question"] = False
                        _clear_current_turn()
                        _queue_progress_sync()
                        st.rerun()

            with col_skip:
                if st.button(get_ui_text("skip_question")):
                    record_current_stress(st.session_state["current_question_num"])

                    st.session_state["interview_history"].append(
                        {
                            "role": "user",
                            "content": "[Skipped]",
                            "timestamp": time.time(),
                        }
                    )
                    _persist_confirmed_turn(
                        "[Skipped]",
                        is_followup=st.session_state.get(
                            "current_question_is_followup",
                            False,
                        ),
                        transcription_engine="typed",
                    )
                    st.session_state["current_question_num"] += 1
                    st.session_state["awaiting_question"] = True
                    st.session_state["awaiting_followup"] = False
                    _clear_current_turn()

                    if (
                        st.session_state["current_question_num"]
                        > st.session_state["total_questions"]
                    ):
                        st.session_state["interview_complete"] = True
                        save_to_question_bank()
                    else:
                        _queue_progress_sync()

                    st.rerun()

            with col_end:
                if st.button(get_ui_text("end_session")):
                    st.session_state["interview_complete"] = True
                    save_to_question_bank()
                    st.rerun()


def _render_legacy_interview_results():
    """Retain the previous multi-feature report for migration reference only."""
    pending_writes = st.session_state.get("_database_pending_writes", [])
    if pending_writes:
        status = database.flush_writes(
            pending_writes,
            timeout_seconds=2.0,
        )
        st.session_state["_database_pending_writes"] = status.pending
        if status.errors:
            st.session_state["_database_sync_error"] = status.errors[-1][:500]

    assessment = st.session_state.get("evidence_assessment")
    assessment_available = bool(assessment and assessment.get("available"))
    company_name = company_prep.get_company_info(
        st.session_state.get("selected_company", "general")
    )["name"]
    ui_theme.render_results_header(
        interview_type=st.session_state.get("interview_type", "Mixed"),
        company=company_name,
        score=(
            float(assessment["overall_score_5"])
            if assessment_available
            and isinstance(assessment.get("overall_score_5"), (int, float))
            else None
        ),
        reliability=(
            str(assessment.get("overall_reliability", "Unavailable"))
            if assessment_available
            else "Not assessed"
        ),
    )

    # Stop video recording if enabled
    if st.session_state.get("video_recording_enabled"):
        video_recording.stop_recording_session()
        st.info(
            "Your interview recording has been saved and is available below."
        )

    st.markdown("## Evidence-based assessment")
    st.caption(
        "HireSense scores relevance, specificity, demonstrated skills, reasoning, "
        "ownership, clarity, and results. Every score must cite words verified "
        "against your transcript."
    )

    button_label = (
        "Retry evidence assessment"
        if assessment and not assessment_available
        else "Generate evidence assessment"
    )
    if not assessment_available:
        if assessment:
            st.warning(
                "No verified score was produced. "
                f"{assessment.get('error', 'Insufficient evidence.')}"
            )
        if st.button(button_label, type="primary"):
            with st.spinner(
                "HireSense is checking every score against the transcript..."
            ):
                company_report_prompt = company_prep.get_company_report_prompt(
                    st.session_state.get("selected_company", "general")
                )
                enhanced_context = (
                    f"{st.session_state['interview_rag_context']}\n\n"
                    f"{company_report_prompt}"
                )
                assessment = evidence_scoring.evaluate_interview(
                    enhanced_context,
                    st.session_state["interview_history"],
                )
                report_text = evidence_scoring.format_assessment_markdown(assessment)
                st.session_state["evidence_assessment"] = assessment
                st.session_state["evidence_assessment_error"] = assessment.get("error")
                st.session_state["interview_report"] = report_text
                _update_saved_assessment(assessment, report_text)
                st.rerun()
    else:
        st.success(
            f"Evidence score: {assessment['overall_score_5']:.2f}/5 | "
            f"Reliability: {assessment['overall_reliability']} | "
            f"Coverage: {assessment['available_dimensions']}/"
            f"{assessment['total_dimensions']} dimensions"
        )
        with st.expander("View evidence report", expanded=True):
            st.markdown(st.session_state.get("interview_report", ""))

    st.markdown("---")
    st.markdown(f"## {get_ui_text('performance_analytics')}")

    analytics.render_full_dashboard(
        st.session_state["interview_stress_timeline"],
        st.session_state["interview_history"],
        st.session_state["total_questions"],
        st.session_state.get("interview_report"),
        evidence_assessment=st.session_state.get("evidence_assessment"),
    )

    # Skill Gap Analysis in Results (NEW)
    if st.session_state.get("skill_analysis_result"):
        st.markdown("---")
        st.markdown("### Skill gap analysis")

        result = st.session_state["skill_analysis_result"]
        gap_analysis = result.get("gap_analysis", {})

        # Show development priorities
        priorities = gap_analysis.get("development_priorities", [])
        if priorities:
            st.markdown("#### Development priorities")
            for priority in priorities[:3]:
                with st.expander(priority.get("area", "Unknown")):
                    st.markdown(
                        f"**Current Gap:** {priority.get('current_gap', 'Unknown')}"
                    )
                    st.markdown(f"**Timeline:** {priority.get('timeline', 'Unknown')}")
                    st.markdown("**Recommended Actions:**")
                    for action in priority.get("recommended_actions", []):
                        st.markdown(f"- {action}")

        # Generate learning path
        if st.button("Generate learning path"):
            skill_gaps = gap_analysis.get("skill_gaps", [])
            if skill_gaps:
                with st.spinner("Generating personalized learning path..."):
                    learning_gen = skill_gap_analysis.generate_learning_path(skill_gaps)
                    display_streaming_response(learning_gen)

    st.markdown("---")

    # Interview Transcript
    with st.expander(get_ui_text("full_transcript")):
        for entry in st.session_state["interview_history"]:
            role = "HireSense" if entry["role"] == "assistant" else "You"
            followup_tag = " (Follow-up)" if entry.get("is_followup") else ""
            st.markdown(f"**{role}{followup_tag}:** {entry['content']}")
            st.markdown("---")

    # Video Recording Playback (NEW)
    if st.session_state.get("video_recording_enabled"):
        with st.expander("Interview recording"):
            video_recording.render_recordings_list(height=200)

    # Non-Verbal Communication Analysis (NEW)
    if st.session_state.get("video_recording_enabled"):
        st.markdown("---")
        st.markdown("### Advanced non-verbal analysis")
        st.markdown(
            "Analyze your eye contact, posture, and filler word usage from your recorded interview."
        )

        # Check if analysis has been done
        if not st.session_state.get("nonverbal_analysis_done"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(
                    "Analyze non-verbal communication",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["show_nonverbal_analysis"] = True
                    st.rerun()

        # Show analysis component
        if st.session_state.get("show_nonverbal_analysis"):
            st.info("Analysis in progress. This may take a few moments.")

            # Render the analysis component
            st.iframe(
                nonverbal_analysis.get_nonverbal_analysis_component_html(
                    video_blob_url="",  # Will be populated from sessionStorage
                    height=700,
                ),
                height=720,
            )

            # Display results if available
            if st.session_state.get("nonverbal_results"):
                results = st.session_state["nonverbal_results"]

                st.markdown("#### Analysis results")

                # Metrics row
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric(
                        "Overall score",
                        f"{results.get('overall', {}).get('score', 'N/A')}/100",
                        delta=results.get("overall", {}).get("rating", ""),
                    )
                with metric_cols[1]:
                    st.metric(
                        "Eye contact",
                        f"{results.get('eyeContact', {}).get('percentage', 'N/A')}%",
                    )
                with metric_cols[2]:
                    st.metric(
                        "🪑 Posture",
                        f"{results.get('posture', {}).get('score', 'N/A')}/100",
                    )
                with metric_cols[3]:
                    st.metric(
                        "Filler words",
                        f"{results.get('fillerWords', {}).get('percentage', 'N/A')}%",
                    )

                # Detailed AI analysis
                if st.button("Generate detailed AI analysis"):
                    with st.spinner("Generating detailed analysis..."):
                        # Create analysis result object
                        analysis_result = nonverbal_analysis.NonVerbalAnalysisResult(
                            session_id="current",
                            analysis_timestamp=datetime.now().isoformat(),
                            video_duration_seconds=st.session_state.get(
                                "interview_duration", 300
                            ),
                            eye_contact=nonverbal_analysis.EyeContactMetrics(
                                total_duration_seconds=st.session_state.get(
                                    "interview_duration", 300
                                ),
                                looking_at_camera_seconds=0,
                                looking_away_seconds=0,
                                eye_contact_percentage=results.get(
                                    "eyeContact", {}
                                ).get("percentage", 0),
                                longest_eye_contact_streak=results.get(
                                    "eyeContact", {}
                                ).get("longestStreak", 0),
                                average_gaze_duration=0,
                                look_away_count=results.get("eyeContact", {}).get(
                                    "lookAwayCount", 0
                                ),
                                rating=nonverbal_analysis.calculate_eye_contact_rating(
                                    results.get("eyeContact", {}).get("percentage", 0)
                                ),
                                feedback="",
                            ),
                            posture=nonverbal_analysis.PostureMetrics(
                                total_frames_analyzed=100,
                                good_posture_frames=results.get("posture", {}).get(
                                    "score", 0
                                ),
                                slouching_frames=results.get("posture", {}).get(
                                    "slouching", 0
                                ),
                                leaning_frames=results.get("posture", {}).get(
                                    "leaning", 0
                                ),
                                posture_score=results.get("posture", {}).get(
                                    "score", 0
                                ),
                                posture_indicators=[],
                                improvement_areas=[],
                                rating=nonverbal_analysis.calculate_posture_rating(
                                    results.get("posture", {}).get("score", 0)
                                ),
                                feedback="",
                            ),
                            filler_words=nonverbal_analysis.FillerWordMetrics(
                                total_words_spoken=results.get("fillerWords", {}).get(
                                    "total", 0
                                )
                                * 20,
                                total_filler_words=results.get("fillerWords", {}).get(
                                    "total", 0
                                ),
                                filler_word_percentage=results.get(
                                    "fillerWords", {}
                                ).get("percentage", 0),
                                filler_breakdown=results.get("fillerWords", {}).get(
                                    "breakdown", {}
                                ),
                                words_per_minute=120,
                                filler_words_per_minute=0,
                                rating="good",
                                feedback="",
                                worst_offenders=list(
                                    results.get("fillerWords", {})
                                    .get("breakdown", {})
                                    .items()
                                )[:5],
                            ),
                            overall_score=results.get("overall", {}).get("score", 0),
                            overall_rating=results.get("overall", {}).get(
                                "rating", "N/A"
                            ),
                            key_strengths=[],
                            areas_for_improvement=[],
                            personalized_tips=[],
                        )

                        # Generate detailed report
                        report_gen = (
                            nonverbal_analysis.generate_detailed_analysis_report(
                                analysis_result,
                                interview_context=st.session_state.get(
                                    "interview_type", "General"
                                ),
                            )
                        )

                        detailed_report = display_streaming_response(report_gen)
                        st.session_state["nonverbal_detailed_report"] = detailed_report

                # Show detailed report if generated
                if st.session_state.get("nonverbal_detailed_report"):
                    with st.expander(
                        "📝 Detailed Non-Verbal Analysis Report", expanded=True
                    ):
                        st.markdown(st.session_state["nonverbal_detailed_report"])

    # Restart option
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            get_ui_text("start_new_session"), type="primary", width="stretch"
        ):
            _cancel_question_prefetch()
            keys_to_reset = [
                "interview_started",
                "interview_complete",
                "interview_history",
                "interview_stress_timeline",
                "current_question_num",
                "interview_report",
                "evidence_assessment",
                "evidence_assessment_error",
                "awaiting_question",
                "interview_start_time",
                "current_question_text",
                "tts_played",
                "current_voice_answer",
                "followup_count",
                "awaiting_followup",
                "current_question_is_followup",
                "current_question_revision",
                "last_followup_decision",
                "rephrase_notice",
                "skill_analysis_done",
                "_interview_orchestrator",
                "_next_question_prefetch",
                "_latency_session_id",
                "latency_samples",
                "active_interview_id",
                "active_application_id",
                "active_job_id",
                "_database_sync_ready",
                "_database_completion_queued_for",
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    if key in {
                        "interview_history",
                        "interview_stress_timeline",
                        "latency_samples",
                    }:
                        st.session_state[key] = []
                    elif key == "current_question_num":
                        st.session_state[key] = 0
                    elif key == "followup_count":
                        st.session_state[key] = 0
                    elif key == "current_question_revision":
                        st.session_state[key] = 0
                    elif key in [
                        "interview_started",
                        "interview_complete",
                        "tts_played",
                        "awaiting_followup",
                        "current_question_is_followup",
                        "skill_analysis_done",
                        "_database_sync_ready",
                    ]:
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = None
            st.rerun()


def _reset_live_voice_interview() -> None:
    """Reset one completed interview while retaining the uploaded context."""
    _cancel_question_prefetch()
    st.session_state.update(
        {
            "interview_started": False,
            "interview_complete": False,
            "interview_history": [],
            "interview_stress_timeline": [],
            "facial_support_questions": [],
            "current_question_num": 0,
            "interview_report": None,
            "evidence_assessment": None,
            "evidence_assessment_error": None,
            "awaiting_question": True,
            "interview_start_time": None,
            "current_question_text": None,
            "current_question_source": None,
            "current_question_status": None,
            "tts_played": False,
            "current_voice_answer": "",
            "followup_count": 0,
            "total_followups_asked": 0,
            "awaiting_followup": False,
            "current_question_is_followup": False,
            "current_question_revision": 0,
            "last_followup_decision": None,
            "rephrase_notice": None,
            "_interview_orchestrator": None,
            "_next_question_prefetch": None,
            "_latency_session_id": None,
            "latency_samples": [],
            "active_interview_id": None,
            "active_application_id": None,
            "active_job_id": None,
            "_database_sync_ready": False,
            "_database_completion_queued_for": None,
        }
    )
    _enforce_live_voice_product_defaults()


def render_interview_results() -> None:
    """Render concise, transcript-grounded feedback for the voice interview."""
    pending_writes = st.session_state.get("_database_pending_writes", [])
    if pending_writes:
        status = database.flush_writes(
            pending_writes,
            timeout_seconds=2.0,
        )
        st.session_state["_database_pending_writes"] = status.pending
        if status.errors:
            st.session_state["_database_sync_error"] = status.errors[-1][:500]

    assessment = st.session_state.get("evidence_assessment")
    assessment_available = bool(assessment and assessment.get("available"))
    ui_theme.render_voice_only_results_header(
        score=(
            float(assessment["overall_score_5"])
            if assessment_available
            and isinstance(assessment.get("overall_score_5"), (int, float))
            else None
        ),
        reliability=(
            str(assessment.get("overall_reliability", "Unavailable"))
            if assessment_available
            else "Not assessed"
        ),
    )

    st.markdown("## Feedback from your answers")
    st.caption(
        "HireSense reviews what you said. A score is shown only when it can be "
        "supported by an exact excerpt from your interview transcript."
    )

    if not assessment_available:
        if assessment:
            st.warning(
                "Feedback could not be completed yet. "
                f"{assessment.get('error', 'There was not enough evidence.')}"
            )
        if st.button("Generate my feedback", type="primary", width="stretch"):
            with st.spinner("Reviewing your answers..."):
                assessment = evidence_scoring.evaluate_interview(
                    st.session_state.get("interview_rag_context", ""),
                    st.session_state.get("interview_history", []),
                )
                report_text = evidence_scoring.format_assessment_markdown(
                    assessment
                )
                st.session_state["evidence_assessment"] = assessment
                st.session_state["evidence_assessment_error"] = assessment.get(
                    "error"
                )
                st.session_state["interview_report"] = report_text
                _update_saved_assessment(assessment, report_text)
            st.rerun()
    else:
        st.success(
            f"Answer score: {assessment['overall_score_5']:.2f}/5 · "
            f"Reliability: {assessment['overall_reliability']} · "
            f"Evidence found for {assessment['available_dimensions']} of "
            f"{assessment['total_dimensions']} areas"
        )
        st.markdown(st.session_state.get("interview_report", ""))

    delivery_summary = confidence_model.summarize_interview_delivery(
        st.session_state.get("interview_history", [])
    )
    if delivery_summary:
        st.markdown("### Speaking delivery")
        st.info(
            f"{delivery_summary['label']} · approximately "
            f"{delivery_summary['score']}/100 · "
            f"{delivery_summary['reliability']} reliability"
        )
        delivery_col1, delivery_col2 = st.columns(2)
        with delivery_col1:
            st.markdown("**What sounded strong**")
            for item in delivery_summary.get("strengths", []):
                st.markdown(f"- {item}")
        with delivery_col2:
            st.markdown("**What to practise next**")
            for item in delivery_summary.get("opportunities", []):
                st.markdown(f"- {item}")
        st.caption(delivery_summary["disclaimer"])

    facial_summary = webcam.summarize_facial_expression_timeline(
        st.session_state.get("interview_stress_timeline", [])
    )
    if facial_summary:
        st.markdown("### Viva Defense facial-expression coaching")
        st.info(facial_summary["label"])
        facial_col1, facial_col2, facial_col3 = st.columns(3)
        facial_col1.metric(
            "Confident-like",
            facial_summary["confident_like_count"],
        )
        facial_col2.metric(
            "Uncertain",
            facial_summary["uncertain_count"],
        )
        facial_col3.metric(
            "Stressed-like",
            facial_summary["stressed_like_count"],
        )
        support_questions = st.session_state.get(
            "facial_support_questions",
            [],
        )
        if support_questions:
            st.caption(
                "Maya used calmer wording after repeated stressed-like "
                f"checkpoints on {len(support_questions)} question"
                f"{'s' if len(support_questions) != 1 else ''}. The planned "
                "competency and difficulty did not change."
            )
        st.caption(
            f"{facial_summary['checkpoint_count']} question-level checkpoints. "
            "Frames were processed in the browser and were not saved."
        )
        with st.expander("How to interpret this model"):
            st.markdown(
                "Viva Defense was trained on FER2013-derived expression groups: "
                "**Happy + Neutral → Confident-like** and "
                "**Fear + Anger + Sadness → Stressed-like**. Its reported test "
                "accuracy is about **85.1%**, while its reported ROC AUC is "
                "**0.9349**. These are different metrics."
            )
            st.caption(facial_summary["disclaimer"])
            st.markdown(
                "[View the Viva Defense model repository]"
                f"({webcam.MODEL_SOURCE_URL})"
            )
    elif st.session_state.get("facial_signal_consent", False):
        st.markdown("### Viva Defense facial-expression coaching")
        st.warning(
            "No usable facial checkpoints were captured. Your answer feedback "
            "is still available and was not affected."
        )

    with st.expander("View interview transcript", expanded=False):
        for entry in st.session_state.get("interview_history", []):
            role = "Interviewer" if entry.get("role") == "assistant" else "You"
            followup = " (follow-up)" if entry.get("is_followup") else ""
            st.markdown(f"**{role}{followup}:** {entry.get('content', '')}")

    st.markdown("---")
    new_col1, new_col2, new_col3 = st.columns([1, 2, 1])
    with new_col2:
        if st.button(
            "Start another live voice interview",
            type="primary",
            width="stretch",
        ):
            _reset_live_voice_interview()
            st.rerun()


def render_question_bank():
    """Render the Question Bank page showing past interviews."""
    ui_theme.render_page_header(
        "Interview history",
        "Review the evidence behind your progress",
        (
            "Return to past answers, compare scoring coverage, and reopen the "
            "transcript that supports each assessment."
        ),
    )

    history = st.session_state.get("question_bank", [])

    if not history:
        ui_theme.render_empty_state(
            "01",
            "No interviews saved yet",
            "Complete your first practice interview and its transcript will appear here.",
        )
        if st.button("Start your first interview", type="primary"):
            st.session_state["page"] = "interview"
            st.rerun()
        return

    filter_col1, filter_col2, count_col = st.columns([2, 2, 1])
    all_types = sorted(set(i.get("interview_type", "Mixed") for i in history))
    with filter_col1:
        selected_filter = st.selectbox("Interview type", ["All"] + all_types)

    all_companies = sorted(set(i.get("company", "general") for i in history))
    company_names = {c: company_prep.get_company_info(c)["name"] for c in all_companies}
    with filter_col2:
        selected_company_filter = st.selectbox(
            "Company", ["All"] + [company_names.get(c, c) for c in all_companies]
        )
    with count_col:
        st.metric("Saved", len(history))

    filtered_history = history
    if selected_filter != "All":
        filtered_history = [
            i for i in filtered_history if i.get("interview_type") == selected_filter
        ]
    if selected_company_filter != "All":
        company_key = next(
            (k for k, v in company_names.items() if v == selected_company_filter), None
        )
        if company_key:
            filtered_history = [
                i for i in filtered_history if i.get("company") == company_key
            ]

    for interview in reversed(filtered_history):
        timestamp = interview.get("timestamp", "Unknown date")
        interview_type = interview.get("interview_type", "General")
        company = interview.get("company", "general")
        company_info = company_prep.get_company_info(company)
        questions = interview.get("questions", [])
        metrics = interview.get("metrics", {})
        with st.expander(
            f"{interview_type} · {company_info['name']} · {timestamp[:10]} · {len(questions)} answers",
            expanded=False,
        ):
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Questions", metrics.get("questions_answered", len(questions))
                )
            with col2:
                evidence_score = metrics.get("evidence_score_5")
                st.metric(
                    "Evidence Score",
                    "Not assessed"
                    if evidence_score is None
                    else f"{float(evidence_score):.2f}/5",
                )
            with col3:
                st.metric(
                    "Reliability",
                    metrics.get("evidence_reliability", "Unavailable"),
                )
            with col4:
                st.metric("Duration", metrics.get("duration", "N/A"))

            st.markdown("---")

            # Questions and answers
            for j, qa in enumerate(questions):
                question = qa.get("question", "N/A")
                answer = qa.get("answer", "N/A")

                st.markdown(f"**Q{j + 1}:** {question}")

                if answer == "[Skipped]":
                    st.warning("*Skipped*")
                else:
                    st.markdown(f"**Your answer:** {answer}")

                st.markdown("---")

            # Report
            report = interview.get("report")
            if report:
                with st.expander("View evidence report"):
                    st.markdown(report)

    st.markdown("---")
    with st.expander("Delete interview history", expanded=False):
        st.warning(
            "This permanently deletes your saved interviews, confirmed "
            "transcripts, and evidence scores."
        )
        confirm_delete = st.checkbox(
            "I understand this cannot be undone",
            key="confirm_delete_interview_history",
        )
        if st.button(
            "Delete all interview history",
            type="secondary",
            disabled=not confirm_delete,
        ):
            try:
                if _database_session_ready():
                    _database_service().delete_all_history()
                st.session_state["question_bank"] = []
                st.session_state["_recoverable_interview"] = None
                persistence.clear_browser_storage(
                    "interview_history",
                    key="clear_question_bank",
                )
                st.rerun()
            except Exception as exc:
                st.error(
                    "Interview history was not deleted because the database "
                    f"request failed: {exc}"
                )


def render_skill_analysis_page():
    """Render dedicated Skill Gap Analysis page (NEW)."""
    ui_theme.render_page_header(
        "Role intelligence",
        "See where your experience meets the role",
        (
            "Compare explicit resume evidence with the job requirements and turn "
            "the most important gaps into a practical learning plan."
        ),
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Your resume")
        resume_text = st.text_area(
            "Paste your resume text",
            height=300,
            key="skill_resume_input",
            value=st.session_state.get("interview_resume_text", ""),
            placeholder="Paste your resume content here...",
        )

    with col2:
        st.markdown("#### Job description")
        jd_text = st.text_area(
            "Paste the job description",
            height=300,
            key="skill_jd_input",
            value=st.session_state.get("interview_jd_text", ""),
            placeholder="Paste the job description here...",
        )

    if st.button("Analyze skills", type="primary", disabled=not (resume_text and jd_text)):
        with st.spinner("Comparing skills and role requirements..."):
            result = skill_gap_analysis.run_full_skill_analysis(resume_text, jd_text)
            st.session_state["skill_page_result"] = result

    if st.session_state.get("skill_page_result"):
        result = st.session_state["skill_page_result"]
        stats = result.get("summary_stats", {})
        gap_analysis = result.get("gap_analysis", {})

        st.markdown("---")
        if not result.get("available", False):
            st.warning(
                result.get("error") or "Skill analysis is currently unavailable."
            )
            st.markdown(
                result.get(
                    "formatted_report",
                    "No role-match score was produced.",
                )
            )
            return

        # Summary metrics
        metric_cols = st.columns(5)
        with metric_cols[0]:
            score = stats.get("overall_score")
            st.metric(
                "Match Score",
                f"{score}%" if isinstance(score, (int, float)) else "N/A",
            )
        with metric_cols[1]:
            st.metric("Category", stats.get("match_category", "Unknown"))
        with metric_cols[2]:
            st.metric("Matching", stats.get("matching_count", 0))
        with metric_cols[3]:
            st.metric("Gaps", stats.get("gap_count", 0))
        with metric_cols[4]:
            st.metric("Exceeding", stats.get("exceeding_count", 0))

        # Radar chart
        st.markdown("---")
        st.markdown("#### Skill category analysis")
        radar_data = result.get("radar_data", {})
        if radar_data.get("categories"):
            st.iframe(
                skill_gap_analysis.get_skill_gap_chart_html(radar_data), height=400
            )

        # Detailed report
        st.markdown("---")
        st.markdown("#### Detailed analysis")
        st.markdown(result.get("formatted_report", "No analysis available"))

        # Learning path generation
        st.markdown("---")
        st.markdown("#### Learning path")

        skill_gaps = gap_analysis.get("skill_gaps", [])
        if skill_gaps:
            timeline = st.slider("Target timeline (months)", 1, 12, 3)

            if st.button("Generate Personalized Learning Path"):
                with st.spinner("Creating your learning path..."):
                    learning_gen = skill_gap_analysis.generate_learning_path(
                        skill_gaps, target_timeline_months=timeline
                    )
                    display_streaming_response(learning_gen)


def render_copilot_page():
    """Render live coaching templates for practice sessions."""
    ui_theme.render_page_header(
        "Coaching practice",
        "Build stronger answer structures",
        (
            "Recognise common interview question patterns and practise shaping "
            "clear, evidence-rich answers before a real conversation."
        ),
    )

    st.info("""
    **How it works:**
    1. Add your resume and job description.
    2. Start listening during a mock interview.
    3. HireSense detects common question patterns.
    4. Review a clearly labelled structural coaching template.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Your resume")
        resume_text = st.text_area(
            "Paste your resume text",
            height=200,
            key="copilot_resume_input",
            value=st.session_state.get("interview_resume_text", ""),
            placeholder="Paste your resume content here...",
        )
        if resume_text:
            st.session_state["interview_resume_text"] = resume_text

    with col2:
        st.markdown("#### Job description")
        jd_text = st.text_area(
            "Paste the job description",
            height=200,
            key="copilot_jd_input",
            value=st.session_state.get("interview_jd_text", ""),
            placeholder="Paste the job description here...",
        )
        if jd_text:
            st.session_state["interview_jd_text"] = jd_text

    st.markdown("---")

    # Copilot activation
    if resume_text and jd_text:
        st.success("Resume and job description are ready.")

        st.markdown("### Live coaching templates")
        st.markdown(
            "The browser detects common question types and shows structural "
            "answer templates. These templates are not live LLM responses."
        )

        # Render the copilot component
        live_copilot.render_copilot_component(
            resume_text=resume_text, jd_text=jd_text, height=700
        )
    else:
        st.warning(
            "Provide both your resume and the job description to activate coaching."
        )


def render_coding_page():
    """Render the Integrated Coding & Whiteboard page (NEW)."""
    ui_theme.render_page_header(
        "Technical practice",
        "Think through code and system design",
        (
            "Use a focused drafting space for coding questions and whiteboard-style "
            "reasoning. The current editor does not execute code."
        ),
    )

    # Problem selection
    st.markdown("#### Select a problem category")

    problem_templates = coding_whiteboard.get_problem_selector()

    # Category selection
    category_cols = st.columns(len(problem_templates))
    selected_category = st.session_state.get("selected_problem_category", "arrays")

    for i, (cat_key, cat_data) in enumerate(problem_templates.items()):
        with category_cols[i]:
            is_selected = selected_category == cat_key
            if st.button(
                cat_data["name"],
                key=f"cat_{cat_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_problem_category"] = cat_key
                st.session_state["current_problem"] = None
                st.rerun()

    # Problem selection within category
    if selected_category:
        category_data = problem_templates.get(selected_category, {})
        problems = category_data.get("problems", [])

        if problems:
            st.markdown(f"#### {category_data['name']} problems")

            problem_options = [f"{p['title']} ({p['difficulty']})" for p in problems]
            selected_problem_idx = st.selectbox(
                "Choose a problem:",
                range(len(problem_options)),
                format_func=lambda x: problem_options[x],
                key="problem_selector",
            )

            if selected_problem_idx is not None:
                st.session_state["current_problem"] = problems[selected_problem_idx]

    # Language selection
    st.markdown("---")
    languages = coding_whiteboard.get_supported_languages()
    lang_options = {v["name"]: k for k, v in languages.items()}

    selected_lang_name = st.selectbox(
        "Programming Language:",
        list(lang_options.keys()),
        index=0,
        key="coding_language_selector",
    )
    selected_language = lang_options[selected_lang_name]
    st.session_state["coding_language"] = selected_language

    st.markdown("---")

    # Render the coding component
    current_problem = st.session_state.get("current_problem")

    coding_whiteboard.render_coding_component(
        initial_language=selected_language,
        initial_code=languages[selected_language].get("default_code", ""),
        problem=current_problem,
        height=750,
    )


# ============================================================================
# Main Application
# ============================================================================


def main() -> None:
    """Main entry point for HireSense AI."""
    st.set_page_config(
        page_title="HireSense AI | Live Voice Interview",
        layout="wide",
        page_icon=(
            str(ui_theme.BRAND_LOGO_PATH)
            if ui_theme.BRAND_LOGO_PATH.is_file()
            else "🎯"
        ),
        initial_sidebar_state="collapsed",
    )

    ui_theme.apply_theme()

    # Initialize session state
    init_session_state()

    if st.session_state.pop("_clear_supabase_session_pending", False):
        persistence.clear_supabase_session(
            key=f"clear_supabase_session_{uuid4().hex}"
        )
    if st.session_state.pop("_clear_supabase_oauth_pending", False):
        persistence.clear_google_oauth_artifacts(
            key=f"clear_supabase_oauth_{uuid4().hex}"
        )

    if not CONFIG_IS_VALID and not st.session_state.get("interview_started"):
        st.warning(
            "OpenRouter is not configured. Built-in interview questions remain "
            "available, but personalized questions and feedback will be "
            "unavailable until OPENROUTER_API_KEY is set."
        )

    # Supabase Auth takes precedence when database sync is enabled because its
    # user JWT is what makes Row Level Security enforceable.
    using_supabase_auth = supabase_auth.auth_required()
    if using_supabase_auth:
        if not st.session_state.get("logged_in", False):
            supabase_auth.render_login_screen()
            st.stop()
        if not supabase_auth.refresh_if_needed():
            supabase_auth.render_login_screen()
            st.stop()
    elif auth.auth_required():
        if not st.session_state.get("logged_in", False):
            auth.render_login_screen()
            st.stop()
    elif not st.session_state.get("logged_in", False):
        st.session_state["logged_in"] = True
        st.session_state["uid"] = "local-user"
        st.session_state["email"] = ""
        st.session_state["display_name"] = "Local User"
        st.session_state["photo_url"] = ""

    supabase_session = st.session_state.pop(
        "_save_supabase_session_pending",
        None,
    )
    if supabase_session:
        persistence.save_supabase_session(
            supabase_session,
            key=(
                "save_supabase_session_"
                f"{int(float(supabase_session.get('expires_at', 0)))}"
            ),
        )

    # Persist only the server-signed token, never raw identity fields.
    auth_token = st.session_state.pop("_save_auth_token_pending", None)
    if auth_token:
        st.iframe(auth._get_save_auth_html(auth_token), height=0)

    # Restore per-user browser data through a bidirectional component.
    persisted = persistence.load_persisted_data()
    if persisted and not st.session_state.get("_persistence_restored"):
        if not st.session_state.get("interview_resume_text"):
            st.session_state["interview_resume_text"] = persisted["resume_text"] or None
        if not st.session_state.get("interview_jd_text"):
            st.session_state["interview_jd_text"] = persisted["jd_text"] or None
        if not st.session_state.get("question_bank"):
            st.session_state["question_bank"] = persisted["interview_history"]
        if st.session_state.get("selected_language", "en") == "en":
            st.session_state["selected_language"] = persisted["language"]
        st.session_state["_persistence_restored"] = True
        st.rerun()

    _collect_database_writes()
    _restore_database_data()
    _enforce_live_voice_product_defaults()

    # Keep account controls available without exposing unrelated workspaces.
    with st.sidebar:
        ui_theme.render_brand(compact=True)
        ui_theme.render_sidebar_profile(
            str(st.session_state.get("display_name") or "HireSense User"),
            str(st.session_state.get("email") or "Local workspace"),
        )

        if using_supabase_auth:
            if st.button("Sign out", key="auth_logout_sidebar", width="stretch"):
                pending = st.session_state.get("_database_pending_writes", [])
                if pending:
                    database.flush_writes(pending, timeout_seconds=2.0)
                supabase_auth.sign_out()
                st.session_state["_persistence_restored"] = False
                st.rerun()
        elif auth.auth_required():
            if st.button("Sign out", key="auth_logout_sidebar", width="stretch"):
                st.session_state["logged_in"] = False
                st.session_state["uid"] = None
                st.session_state["email"] = None
                st.session_state["display_name"] = None
                st.session_state["photo_url"] = None
                st.session_state["_persistence_restored"] = False
                st.iframe(auth._get_clear_auth_html(), height=0)
                st.rerun()

        ui_theme.render_sidebar_label("Current product")
        st.markdown("**Live Voice Interview**")
        st.caption("Personalized voice practice with transcript-based feedback.")

        if config.developer_controls_enabled():
            with st.expander("Developer status", expanded=False):
                config_status = config.get_config_status()
                router_state = (
                    "Connected"
                    if config_status["openrouter"]["configured"]
                    else "Not configured"
                )
                tracing_state = (
                    config_status["langsmith"]["project"]
                    if config_status["langsmith"]["enabled"]
                    else "Disabled"
                )
                st.caption(f"Question service: {router_state}")
                st.caption(
                    f"Model: {config_status['openrouter']['model']}"
                )
                st.caption(f"Tracing: {tracing_state}")
                st.caption(
                    "Supabase: "
                    + (
                        "Connected"
                        if _database_session_ready()
                        else "Not configured"
                    )
                )
                if st.session_state.get("_database_sync_error"):
                    st.caption(
                        "Last sync issue: "
                        + str(st.session_state["_database_sync_error"])[:180]
                    )

    if (
        st.session_state["interview_started"]
        and not st.session_state["interview_complete"]
    ):
        render_live_voice_session()
    elif st.session_state["interview_complete"]:
        render_interview_results()
    else:
        render_interview_setup()

    ui_theme.render_footer(
        (
            "Live voice practice",
            "Personalized questions",
            "Transcript-based feedback",
        )
    )


if __name__ == "__main__":
    main()
