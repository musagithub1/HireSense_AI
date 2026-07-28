"""Small, dependency-light Supabase HTTP client for HireSense.

The browser-facing application uses only a Supabase publishable/anon key plus
the signed-in user's access token. A service-role key is intentionally neither
accepted nor required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


class SupabaseError(RuntimeError):
    """A sanitized Supabase API failure."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message[:500])
        self.status_code = status_code


def _streamlit_secret(name: str) -> str:
    """Read root or [supabase] Streamlit secrets without requiring Streamlit."""
    try:
        import streamlit as st

        root_value = st.secrets.get(name, "")
        if root_value:
            return str(root_value).strip()

        section = st.secrets.get("supabase", {})
        if section:
            aliases = {
                "SUPABASE_URL": ("url", "project_url"),
                "SUPABASE_PUBLISHABLE_KEY": (
                    "publishable_key",
                    "anon_key",
                    "key",
                ),
                "SUPABASE_ANON_KEY": ("anon_key", "publishable_key", "key"),
            }
            for alias in aliases.get(name, (name.lower(),)):
                value = section.get(alias, "")
                if value:
                    return str(value).strip()
    except Exception:
        pass
    return ""


def setting(name: str, default: str = "") -> str:
    """Read a setting from the environment, then Streamlit Secrets."""
    return os.environ.get(name, "").strip() or _streamlit_secret(name) or default


def boolean_setting(name: str, default: bool = False) -> bool:
    raw = setting(name, "true" if default else "false").casefold()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SupabaseSettings:
    """Validated public connection settings."""

    url: str
    publishable_key: str
    timeout_seconds: float = 10.0

    @classmethod
    def load(cls) -> "SupabaseSettings | None":
        url = setting("SUPABASE_URL").rstrip("/")
        key = setting("SUPABASE_PUBLISHABLE_KEY") or setting("SUPABASE_ANON_KEY")
        if not url or not key:
            return None
        if not url.startswith("https://"):
            local_allowed = boolean_setting(
                "HIRESENSE_ALLOW_INSECURE_LOCAL_SUPABASE",
                default=False,
            )
            if not (
                local_allowed
                and (
                    url.startswith("http://localhost")
                    or url.startswith("http://127.0.0.1")
                )
            ):
                return None
        try:
            timeout = float(setting("SUPABASE_TIMEOUT_SECONDS", "10"))
        except ValueError:
            timeout = 10.0
        return cls(
            url=url,
            publishable_key=key,
            timeout_seconds=max(2.0, min(timeout, 30.0)),
        )


def is_configured() -> bool:
    return SupabaseSettings.load() is not None


def _error_message(response: requests.Response) -> str:
    """Return a useful API message without reflecting credentials or payloads."""
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        for key in ("msg", "message", "error_description", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:500]
    return f"Supabase request failed with status {response.status_code}."


class SupabaseGateway:
    """Authenticated access to Supabase Auth, PostgREST, and Storage."""

    def __init__(
        self,
        settings: SupabaseSettings,
        *,
        access_token: str = "",
        http: requests.Session | None = None,
    ):
        self.settings = settings
        self.access_token = str(access_token).strip()
        self.http = http or requests.Session()

    @classmethod
    def configured(
        cls,
        *,
        access_token: str = "",
        http: requests.Session | None = None,
    ) -> "SupabaseGateway":
        settings = SupabaseSettings.load()
        if settings is None:
            raise SupabaseError(
                "Supabase is not configured. Add SUPABASE_URL and "
                "SUPABASE_PUBLISHABLE_KEY."
            )
        return cls(settings, access_token=access_token, http=http)

    def _headers(
        self,
        *,
        authenticated: bool = True,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        bearer = (
            self.access_token
            if authenticated and self.access_token
            else self.settings.publishable_key
        )
        headers = {
            "apikey": self.settings.publishable_key,
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        data: bytes | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
    ) -> Any:
        try:
            response = self.http.request(
                method,
                f"{self.settings.url}{path}",
                headers=self._headers(authenticated=authenticated, extra=headers),
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=self.settings.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise SupabaseError(
                f"Supabase could not be reached ({exc.__class__.__name__})."
            ) from exc

        if response.status_code not in expected:
            raise SupabaseError(
                _error_message(response),
                status_code=response.status_code,
            )
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    # Auth

    def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        result = self.request(
            "POST",
            "/auth/v1/token",
            authenticated=False,
            params={"grant_type": "password"},
            json_body={"email": email, "password": password},
        )
        return result if isinstance(result, dict) else {}

    def sign_up(
        self,
        email: str,
        password: str,
        *,
        full_name: str,
    ) -> dict[str, Any]:
        result = self.request(
            "POST",
            "/auth/v1/signup",
            authenticated=False,
            json_body={
                "email": email,
                "password": password,
                "data": {"full_name": full_name, "role": "candidate"},
            },
        )
        return result if isinstance(result, dict) else {}

    def refresh_session(self, refresh_token: str) -> dict[str, Any]:
        result = self.request(
            "POST",
            "/auth/v1/token",
            authenticated=False,
            params={"grant_type": "refresh_token"},
            json_body={"refresh_token": refresh_token},
        )
        return result if isinstance(result, dict) else {}

    def get_user(self) -> dict[str, Any]:
        result = self.request("GET", "/auth/v1/user")
        return result if isinstance(result, dict) else {}

    def sign_out(self) -> None:
        self.request("POST", "/auth/v1/logout", expected=(200, 204))

    # PostgREST

    def rpc(self, function_name: str, payload: dict[str, Any]) -> Any:
        safe_name = quote(function_name, safe="_")
        return self.request(
            "POST",
            f"/rest/v1/rpc/{safe_name}",
            json_body=payload,
            headers={"Content-Type": "application/json"},
        )

    def select(
        self,
        table: str,
        *,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        safe_table = quote(table, safe="_")
        result = self.request("GET", f"/rest/v1/{safe_table}", params=params)
        return result if isinstance(result, list) else []

    def insert(
        self,
        table: str,
        payload: dict[str, Any] | list[dict[str, Any]],
        *,
        params: dict[str, Any] | None = None,
        upsert: bool = False,
        return_rows: bool = False,
    ) -> list[dict[str, Any]]:
        prefer = []
        if upsert:
            prefer.append("resolution=merge-duplicates")
        prefer.append(
            "return=representation" if return_rows else "return=minimal"
        )
        safe_table = quote(table, safe="_")
        result = self.request(
            "POST",
            f"/rest/v1/{safe_table}",
            params=params,
            json_body=payload,
            headers={
                "Content-Type": "application/json",
                "Prefer": ",".join(prefer),
            },
        )
        return result if isinstance(result, list) else []

    def update(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        filters: dict[str, Any],
    ) -> None:
        safe_table = quote(table, safe="_")
        self.request(
            "PATCH",
            f"/rest/v1/{safe_table}",
            params=filters,
            json_body=payload,
            headers={
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )

    def delete(self, table: str, *, filters: dict[str, Any]) -> None:
        safe_table = quote(table, safe="_")
        self.request(
            "DELETE",
            f"/rest/v1/{safe_table}",
            params=filters,
            headers={"Prefer": "return=minimal"},
        )

    # Storage

    def upload_pdf(self, path: str, content: bytes) -> None:
        safe_path = quote(path.lstrip("/"), safe="/._-")
        filename = safe_path.rsplit("/", 1)[-1] or "resume.pdf"
        self.request(
            "POST",
            f"/storage/v1/object/resumes/{safe_path}",
            files={"file": (filename, content, "application/pdf")},
            headers={
                "x-upsert": "true",
            },
        )

    def remove_pdfs(self, paths: list[str]) -> None:
        clean_paths = [
            str(path).lstrip("/")[:500]
            for path in paths
            if str(path).strip()
        ]
        if not clean_paths:
            return
        self.request(
            "DELETE",
            "/storage/v1/object/resumes",
            json_body={"prefixes": clean_paths[:100]},
            headers={"Content-Type": "application/json"},
            expected=(200, 204),
        )
