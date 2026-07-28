"""Regression tests for normalized interview persistence and recovery."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

import database

USER_ID = "00000000-0000-0000-0000-000000000001"
INTERVIEW_ID = "00000000-0000-0000-0000-000000000002"
APPLICATION_ID = "00000000-0000-0000-0000-000000000003"
JOB_ID = "00000000-0000-0000-0000-000000000004"


class FakeGateway:
    def __init__(self):
        self.calls = []
        self.select_results: dict[str, list[dict]] = {}

    def rpc(self, name, payload):
        self.calls.append(("rpc", name, payload))
        return [
            {
                "interview_id": INTERVIEW_ID,
                "application_id": APPLICATION_ID,
                "job_id": JOB_ID,
            }
        ]

    def insert(self, table, payload, **kwargs):
        self.calls.append(("insert", table, payload, kwargs))
        return []

    def update(self, table, payload, **kwargs):
        self.calls.append(("update", table, payload, kwargs))

    def select(self, table, **kwargs):
        self.calls.append(("select", table, kwargs))
        return self.select_results.get(table, [])

    def delete(self, table, **kwargs):
        self.calls.append(("delete", table, kwargs))

    def upload_pdf(self, path, content):
        self.calls.append(("upload_pdf", path, content))

    def remove_pdfs(self, paths):
        self.calls.append(("remove_pdfs", paths))


def service(gateway: FakeGateway) -> database.DatabaseService:
    return database.DatabaseService(
        access_token="signed-user-jwt",
        user_id=USER_ID,
        gateway=gateway,
    )


def test_start_interview_uses_single_normalized_rpc() -> None:
    gateway = FakeGateway()

    result = service(gateway).start_interview(
        interview_id=INTERVIEW_ID,
        company_key="general",
        company_name="General",
        job_title="Machine Learning Engineer",
        job_description="Build and deploy models.",
        resume_text="Python and PyTorch.",
        language_key="ur",
        language_code="ur-PK",
        interview_type="Technical",
        mode="live_voice",
        model="deepseek/deepseek-v4-flash",
        total_questions=5,
    )

    assert result["application_id"] == APPLICATION_ID
    call = gateway.calls[0]
    assert call[0:2] == ("rpc", "start_practice_interview")
    assert call[2]["p_language_key"] == "ur"
    assert call[2]["p_language_code"] == "ur-PK"
    assert call[2]["p_mode"] == "live_voice"


def test_confirmed_turn_upsert_is_idempotent_and_language_preserving() -> None:
    gateway = FakeGateway()

    service(gateway).upsert_turn(
        {
            "interview_id": INTERVIEW_ID,
            "turn_index": 1,
            "question_number": 1,
            "question_original": "اپنے تجربے کے بارے میں بتائیں۔",
            "transcript_original": "میں نے Python میں ایک سسٹم بنایا۔",
            "transcript_confirmed": True,
            "language_key": "ur",
            "language_code": "ur-PK",
            "transcription_engine": "browser_speech",
        }
    )

    _, table, payload, options = gateway.calls[0]
    assert table == "interview_turns"
    assert payload["transcript_confirmed"] is True
    assert payload["language_key"] == "ur"
    assert payload["language_code"] == "ur-PK"
    assert payload["english_translation"] is None
    assert options["upsert"] is True
    assert options["params"]["on_conflict"] == "interview_id,turn_index"


def test_assessment_rows_keep_verified_evidence() -> None:
    gateway = FakeGateway()
    assessment = {
        "dimensions": {
            "relevance": {
                "score": 4.0,
                "reason": "Direct answer.",
                "reliability": "Medium",
                "evidence": [
                    {"answer_index": 1, "excerpt": "reduced latency by 30%"}
                ],
            }
        }
    }

    service(gateway).save_assessment(
        interview_id=INTERVIEW_ID,
        assessment=assessment,
        report_markdown="# Report",
        metrics={"evidence_score_5": 4.0},
    )

    score_call = next(
        call
        for call in gateway.calls
        if call[0] == "insert" and call[1] == "evaluation_scores"
    )
    score = score_call[2][0]
    assert score["dimension"] == "relevance"
    assert score["evidence_excerpt"] == "reduced latency by 30%"
    assert score["owner_id"] == USER_ID


def test_recovery_reconstructs_original_question_and_transcript() -> None:
    gateway = FakeGateway()
    gateway.select_results = {
        "interviews": [
            {
                "id": INTERVIEW_ID,
                "application_id": APPLICATION_ID,
                "interview_type": "Technical",
                "company_key": "general",
                "language_key": "hi",
                "language_code": "hi-IN",
                "mode": "live_voice",
                "total_questions": 5,
                "progress": {"current_question_num": 2},
            }
        ],
        "applications": [
            {
                "id": APPLICATION_ID,
                "job_id": JOB_ID,
                "resume_text": "Python engineer",
            }
        ],
        "jobs": [
            {
                "id": JOB_ID,
                "title": "AI Engineer",
                "company_key": "general",
                "description": "Build AI systems",
            }
        ],
        "interview_turns": [
            {
                "turn_index": 1,
                "question_number": 1,
                "is_followup": False,
                "question_original": "अपने अनुभव के बारे में बताइए।",
                "transcript_original": "मैंने एक मॉडल बनाया।",
                "question_source": "model",
                "created_at": "2026-07-28T12:00:00+00:00",
            }
        ],
    }

    recovered = service(gateway).load_recoverable_interview()

    assert recovered is not None
    assert recovered["target_role"] == "AI Engineer"
    assert recovered["language"] == "hi"
    assert recovered["language_code"] == "hi-IN"
    assert recovered["conversation"][0]["content"].startswith("अपने")
    assert recovered["conversation"][1]["content"].startswith("मैंने")


def test_delete_history_removes_private_files_before_database_rows() -> None:
    gateway = FakeGateway()
    gateway.select_results = {
        "applications": [
            {
                "id": APPLICATION_ID,
                "job_id": JOB_ID,
                "resume_path": f"{USER_ID}/{APPLICATION_ID}/resume.pdf",
            }
        ]
    }

    service(gateway).delete_all_history()

    operations = [call[0:2] for call in gateway.calls]
    assert ("remove_pdfs", [f"{USER_ID}/{APPLICATION_ID}/resume.pdf"]) in [
        (call[0], call[1]) for call in gateway.calls if call[0] == "remove_pdfs"
    ]
    assert ("delete", "applications") in operations
    assert ("delete", "jobs") in operations
    assert operations.index(("delete", "applications")) < operations.index(
        ("delete", "jobs")
    )


def test_delete_history_batches_private_resume_removal() -> None:
    gateway = FakeGateway()
    gateway.select_results = {
        "applications": [
            {
                "id": APPLICATION_ID,
                "job_id": JOB_ID,
                "resume_path": f"{USER_ID}/{index}/resume.pdf",
            }
            for index in range(205)
        ]
    }

    service(gateway).delete_all_history()

    removals = [
        call[1] for call in gateway.calls if call[0] == "remove_pdfs"
    ]
    assert [len(paths) for paths in removals] == [100, 100, 5]


def test_schema_enables_rls_and_never_requests_service_role() -> None:
    root = Path(__file__).parents[1]
    schema = (
        root
        / "supabase"
        / "migrations"
        / "202607280001_hiresense_core.sql"
    ).read_text(encoding="utf-8")
    example = (root / ".env.example").read_text(encoding="utf-8")

    for table in (
        "profiles",
        "jobs",
        "applications",
        "interviews",
        "interview_turns",
        "evaluation_scores",
    ):
        assert f"alter table public.{table} enable row level security" in schema
    assert "auth.uid() is not null" in schema
    assert "transcript_confirmed" in schema
    assert "and role = 'candidate'" in schema
    assert schema.count("profiles.role in ('recruiter', 'admin')") == 4
    assert "security definer\nset search_path = ''" in schema
    assert "profiles_protect_role" in schema
    assert "service_role" not in example.casefold()


def test_google_profile_migration_preserves_candidate_role() -> None:
    root = Path(__file__).parents[1]
    migration = (
        root
        / "supabase"
        / "migrations"
        / "202607290001_google_auth_profile.sql"
    ).read_text(encoding="utf-8")

    assert "raw_user_meta_data ->> 'full_name'" in migration
    assert "raw_user_meta_data ->> 'name'" in migration
    assert "'candidate'" in migration
    assert "security definer\nset search_path = ''" in migration
    assert "service_role" not in migration.casefold()


def test_built_persistence_component_supports_auth_session_recovery() -> None:
    root = Path(__file__).parents[1]
    source = (
        root / "persistence" / "frontend" / "src" / "main.js"
    ).read_text(encoding="utf-8")
    bundles = list(
        (root / "persistence" / "frontend" / "dist" / "assets").glob("*.js")
    )

    assert "load_auth" in source
    assert "save_auth" in source
    assert "clear_auth" in source
    assert "supabase_session" in source
    assert 'flowType: "pkce"' in source
    assert 'provider: "google"' in source
    assert "exchangeCodeForSession" in source
    assert 'control.target = "_blank"' in source
    assert 'control.rel = "noopener noreferrer"' in source
    assert 'control.target = "_top"' not in source
    assert "provider_token" not in source
    assert len(bundles) == 1
    bundle = bundles[0].read_text(encoding="utf-8")
    assert "supabase_session" in bundle
    assert "_blank" in bundle
    assert "_top" not in bundle


def test_background_writes_preserve_per_session_order(monkeypatch) -> None:
    calls = []

    class FakeService:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def upsert_turn(self, **payload):
            calls.append(("write", payload))

        update_progress = upsert_turn
        complete_interview = upsert_turn
        save_assessment = upsert_turn
        upload_resume = upsert_turn
        abandon_interview = upsert_turn

    monkeypatch.setattr(database, "DatabaseService", FakeService)
    dependency = Future()
    pending = database.enqueue_operation(
        "Save turn",
        access_token="access",
        user_id=USER_ID,
        operation="upsert_turn",
        payload={"payload": {"interview_id": INTERVIEW_ID}},
        depends_on=dependency,
    )

    assert not pending.future.done()
    assert not calls
    dependency.set_result(None)
    pending.future.result(timeout=2)
    assert calls[0][0] == "init"
    assert calls[1][0] == "write"
