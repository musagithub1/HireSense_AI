"""Security tests for signed OAuth and browser session data."""

from __future__ import annotations

import auth


def test_signed_session_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("HIRESENSE_SESSION_SECRET", "test-secret-with-enough-entropy")
    profile = {
        "uid": "google-user-123",
        "email": "person@example.com",
        "display_name": "Person",
        "photo_url": "https://example.com/avatar.png",
    }
    token = auth.create_session_token(profile)
    assert auth.verify_session_token(token) == profile


def test_tampered_and_expired_tokens_are_rejected(monkeypatch) -> None:
    monkeypatch.setenv("HIRESENSE_SESSION_SECRET", "test-secret-with-enough-entropy")
    token = auth.create_session_token({"uid": "user"})
    replacement = "A" if token[-1] != "A" else "B"
    assert auth.verify_session_token(token[:-1] + replacement) is None

    expired = auth.create_session_token({"uid": "user"}, ttl_seconds=-1)
    assert auth.verify_session_token(expired) is None


def test_auth_configuration_is_explicit(monkeypatch) -> None:
    for name in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REDIRECT_URI",
        "HIRESENSE_SESSION_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HIRESENSE_AUTH_REQUIRED", "false")

    assert auth.auth_required() is False
    assert auth.auth_is_configured() is False
