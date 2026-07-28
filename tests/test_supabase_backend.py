"""Tests for the public-key, user-JWT Supabase transport."""

from __future__ import annotations

import json

import pytest

from supabase_backend import (
    SupabaseError,
    SupabaseGateway,
    SupabaseSettings,
)


class FakeResponse:
    def __init__(self, status: int, payload=None):
        self.status_code = status
        self._payload = payload
        self.content = b"" if payload is None else json.dumps(payload).encode()

    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def settings() -> SupabaseSettings:
    return SupabaseSettings(
        url="https://example.supabase.co",
        publishable_key="sb_publishable_public-test",
        timeout_seconds=7,
    )


def test_rls_requests_use_public_key_and_user_jwt() -> None:
    http = FakeHttp(FakeResponse(200, []))
    gateway = SupabaseGateway(
        settings(),
        access_token="signed-user-jwt",
        http=http,
    )

    gateway.select("interviews", params={"select": "id"})

    _, url, kwargs = http.calls[0]
    assert url == "https://example.supabase.co/rest/v1/interviews"
    assert kwargs["headers"]["apikey"] == "sb_publishable_public-test"
    assert kwargs["headers"]["Authorization"] == "Bearer signed-user-jwt"
    assert "service_role" not in json.dumps(kwargs)


def test_auth_request_uses_public_key_until_user_session_exists() -> None:
    http = FakeHttp(
        FakeResponse(
            200,
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "user": {"id": "00000000-0000-0000-0000-000000000001"},
            },
        )
    )
    gateway = SupabaseGateway(settings(), http=http)

    gateway.sign_in_with_password("person@example.com", "secret-password")

    _, _, kwargs = http.calls[0]
    assert kwargs["params"] == {"grant_type": "password"}
    assert kwargs["headers"]["Authorization"] == (
        "Bearer sb_publishable_public-test"
    )


def test_api_errors_are_sanitized() -> None:
    http = FakeHttp(FakeResponse(401, {"message": "Invalid login credentials"}))
    gateway = SupabaseGateway(settings(), http=http)

    with pytest.raises(SupabaseError, match="Invalid login credentials") as error:
        gateway.get_user()

    assert error.value.status_code == 401
    assert "sb_publishable" not in str(error.value)


def test_storage_delete_is_bounded_to_explicit_paths() -> None:
    http = FakeHttp(FakeResponse(200, {}))
    gateway = SupabaseGateway(
        settings(),
        access_token="signed-user-jwt",
        http=http,
    )

    gateway.remove_pdfs(["user/application/resume.pdf", ""])

    method, url, kwargs = http.calls[0]
    assert method == "DELETE"
    assert url.endswith("/storage/v1/object/resumes")
    assert kwargs["json"] == {
        "prefixes": ["user/application/resume.pdf"]
    }


def test_pdf_upload_uses_storage_multipart_format() -> None:
    http = FakeHttp(FakeResponse(200, {"Key": "resumes/user/resume.pdf"}))
    gateway = SupabaseGateway(
        settings(),
        access_token="signed-user-jwt",
        http=http,
    )

    gateway.upload_pdf("user/application/resume.pdf", b"%PDF-test")

    method, url, kwargs = http.calls[0]
    assert method == "POST"
    assert url.endswith(
        "/storage/v1/object/resumes/user/application/resume.pdf"
    )
    assert kwargs["files"]["file"] == (
        "resume.pdf",
        b"%PDF-test",
        "application/pdf",
    )
    assert kwargs["headers"]["x-upsert"] == "true"
