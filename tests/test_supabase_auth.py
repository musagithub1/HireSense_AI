"""Tests for Supabase Auth session normalization and configuration."""

from __future__ import annotations

import supabase_auth


class FakeQueryParams(dict):
    def to_dict(self) -> dict:
        return dict(self)

    def from_dict(self, value: dict) -> None:
        self.clear()
        self.update(value)


def test_auth_response_normalizes_expiry_and_user() -> None:
    session = supabase_auth._session_from_response(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
            "user": {
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "person@example.com",
            },
        }
    )

    assert session is not None
    assert session["access_token"] == "access"
    assert session["refresh_token"] == "refresh"
    assert session["expires_at"] > 0
    assert session["user"]["email"] == "person@example.com"


def test_incomplete_auth_response_is_rejected() -> None:
    assert (
        supabase_auth._session_from_response(
            {"access_token": "access", "user": {}}
        )
        is None
    )


def test_untrusted_google_session_is_bounded_and_requires_uuid() -> None:
    assert (
        supabase_auth._session_from_response(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "user": {"id": "not-a-supabase-uuid"},
            }
        )
        is None
    )
    assert (
        supabase_auth._session_from_response(
            {
                "access_token": "a" * 16_001,
                "refresh_token": "refresh",
                "user": {
                    "id": "00000000-0000-0000-0000-000000000001",
                },
            }
        )
        is None
    )


def test_google_auth_defaults_on_with_supabase_and_can_be_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv(
        "SUPABASE_PUBLISHABLE_KEY",
        "sb_publishable_public-test",
    )
    monkeypatch.setenv("HIRESENSE_SUPABASE_AUTH_REQUIRED", "true")
    monkeypatch.delenv("HIRESENSE_GOOGLE_AUTH_ENABLED", raising=False)

    assert supabase_auth.google_auth_enabled() is True

    monkeypatch.setenv("HIRESENSE_GOOGLE_AUTH_ENABLED", "false")
    assert supabase_auth.google_auth_enabled() is False


def test_oauth_redirect_override_requires_safe_exact_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "SUPABASE_OAUTH_REDIRECT_URL",
        "https://hiresense.example.com/",
    )
    assert (
        supabase_auth._oauth_redirect_url()
        == "https://hiresense.example.com/"
    )

    monkeypatch.setenv(
        "SUPABASE_OAUTH_REDIRECT_URL",
        "https://hiresense.example.com/?next=https://evil.example",
    )
    assert supabase_auth._oauth_redirect_url() == ""

    monkeypatch.setenv(
        "SUPABASE_OAUTH_REDIRECT_URL",
        "http://localhost:8501/",
    )
    assert supabase_auth._oauth_redirect_url() == "http://localhost:8501/"


def test_google_callback_applies_supabase_session_and_clears_query(
    monkeypatch,
) -> None:
    class FakeStreamlit:
        session_state = {}
        query_params = FakeQueryParams(
            {
                "code": "oauth_code_123456",
                "sb_flow_id": "flow_id_12345678",
                "page": "interview",
            }
        )

    monkeypatch.setattr(supabase_auth, "st", FakeStreamlit)
    monkeypatch.setattr(
        supabase_auth.persistence,
        "exchange_google_oauth_code",
        lambda code, **kwargs: {
            "status": "authenticated",
            "session": {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "user": {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "email": "person@example.com",
                    "app_metadata": {"provider": "google"},
                    "user_metadata": {
                        "full_name": "Person",
                        "avatar_url": "https://example.com/avatar.png",
                    },
                },
            },
        },
    )

    status, message = supabase_auth._process_google_oauth_callback()

    assert (status, message) == ("authenticated", "")
    assert FakeStreamlit.session_state["logged_in"] is True
    assert FakeStreamlit.session_state["auth_provider"] == "google"
    assert FakeStreamlit.session_state["uid"].endswith("0001")
    assert FakeStreamlit.query_params == {"page": "interview"}


def test_invalid_google_callback_never_reaches_exchange(monkeypatch) -> None:
    class FakeStreamlit:
        session_state = {}
        query_params = FakeQueryParams({"code": "<invalid>"})

    monkeypatch.setattr(supabase_auth, "st", FakeStreamlit)
    monkeypatch.setattr(
        supabase_auth.persistence,
        "exchange_google_oauth_code",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("exchange must not run")
        ),
    )
    monkeypatch.setattr(
        supabase_auth.persistence,
        "clear_google_oauth_artifacts",
        lambda **kwargs: None,
    )

    status, message = supabase_auth._process_google_oauth_callback()

    assert status == "error"
    assert "invalid" in message.casefold()
    assert FakeStreamlit.query_params == {}


def test_sign_out_workspace_reset_prevents_cross_user_data(monkeypatch) -> None:
    class FakeStreamlit:
        session_state = {
            "question_bank": [{"id": "private"}],
            "interview_resume_text": "private resume",
            "interview_history": [{"role": "user", "content": "private"}],
            "_database_pending_writes": ["private future"],
        }

    monkeypatch.setattr(supabase_auth, "st", FakeStreamlit)

    supabase_auth._clear_session_state()

    assert FakeStreamlit.session_state["question_bank"] == []
    assert FakeStreamlit.session_state["interview_resume_text"] is None
    assert FakeStreamlit.session_state["interview_history"] == []
    assert FakeStreamlit.session_state["_database_pending_writes"] == []
    assert FakeStreamlit.session_state["uid"] is None
