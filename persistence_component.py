"""Validated, per-user browser persistence for HireSense AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from supabase_backend import SupabaseSettings

_DIST_DIR = Path(__file__).parent / "persistence" / "frontend" / "dist"
_persistence = components.declare_component(
    "hiresense_persistence",
    path=str(_DIST_DIR),
)
_ALLOWED_KEYS = {"resume_text", "jd_text", "interview_history", "language"}


def _namespace() -> str:
    return str(st.session_state.get("uid") or "local-user")[:200]


def load_persisted_data(*, key: str = "persistence_loader") -> dict | None:
    """Load validated data stored for the active user in this browser."""
    value = _persistence(
        operation="load",
        namespace=_namespace(),
        default=None,
        key=key,
    )
    if not isinstance(value, dict) or value.get("status") != "loaded":
        return None

    history = value.get("interview_history")
    if not isinstance(history, list):
        history = []
    history = [item for item in history if isinstance(item, dict)][:100]
    language = str(value.get("language", "en"))[:20]
    return {
        "resume_text": str(value.get("resume_text", ""))[:200_000],
        "jd_text": str(value.get("jd_text", ""))[:200_000],
        "interview_history": history,
        "language": language,
    }


def save_to_browser(storage_key: str, value: Any, *, key: str) -> None:
    """Persist one allowed value under the active user's namespace."""
    if storage_key not in _ALLOWED_KEYS:
        raise ValueError(f"Unsupported persistence key: {storage_key}")
    _persistence(
        operation="save",
        namespace=_namespace(),
        storage_key=storage_key,
        value=value,
        default=None,
        key=key,
    )


def clear_browser_storage(
    storage_key: str = "ALL",
    *,
    key: str = "persistence_clear",
) -> None:
    """Clear one allowed value, or every value for the active user."""
    if storage_key != "ALL" and storage_key not in _ALLOWED_KEYS:
        raise ValueError(f"Unsupported persistence key: {storage_key}")
    _persistence(
        operation="clear",
        namespace=_namespace(),
        storage_key=storage_key,
        default=None,
        key=key,
    )


def load_supabase_session(
    *,
    key: str = "supabase_session_loader",
) -> dict | None:
    """Load a bounded Supabase refresh session from this browser."""
    value = _persistence(
        operation="load_auth",
        namespace="auth",
        default=None,
        key=key,
    )
    if not isinstance(value, dict) or value.get("status") != "loaded":
        return None
    session = value.get("supabase_session")
    if not isinstance(session, dict):
        return None
    access_token = str(session.get("access_token", ""))[:8_000]
    refresh_token = str(session.get("refresh_token", ""))[:8_000]
    try:
        expires_at = float(session.get("expires_at", 0))
    except (TypeError, ValueError):
        expires_at = 0
    if not refresh_token:
        return None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def save_supabase_session(session: dict, *, key: str) -> None:
    """Persist only the tokens needed to restore a Supabase Auth session."""
    if not isinstance(session, dict):
        raise ValueError("Supabase session must be a dictionary.")
    payload = {
        "access_token": str(session.get("access_token", ""))[:8_000],
        "refresh_token": str(session.get("refresh_token", ""))[:8_000],
        "expires_at": float(session.get("expires_at", 0)),
    }
    if not payload["access_token"] or not payload["refresh_token"]:
        raise ValueError("Supabase session tokens are missing.")
    _persistence(
        operation="save_auth",
        namespace="auth",
        value=payload,
        default=None,
        key=key,
    )


def clear_supabase_session(*, key: str = "supabase_session_clear") -> None:
    """Remove the saved Supabase Auth session from this browser."""
    _persistence(
        operation="clear_auth",
        namespace="auth",
        default=None,
        key=key,
    )


def render_google_oauth_button(
    *,
    redirect_to: str = "",
    key: str = "supabase_google_oauth_button",
) -> dict | None:
    """Render the browser-side Supabase Google OAuth PKCE control."""
    settings = SupabaseSettings.load()
    if settings is None:
        return {
            "status": "error",
            "message": "Supabase is not configured.",
        }
    value = _persistence(
        operation="google_oauth_button",
        namespace="auth",
        supabase_url=settings.url,
        supabase_publishable_key=settings.publishable_key,
        redirect_to=str(redirect_to)[:2_000],
        default=None,
        key=key,
    )
    return value if isinstance(value, dict) else None


def exchange_google_oauth_code(
    code: str,
    *,
    flow_id: str = "",
    key: str = "supabase_google_oauth_exchange",
) -> dict | None:
    """Exchange a Supabase PKCE callback code in the originating browser."""
    settings = SupabaseSettings.load()
    if settings is None:
        return {
            "status": "error",
            "message": "Supabase is not configured.",
        }
    value = _persistence(
        operation="exchange_google_oauth",
        namespace="auth",
        supabase_url=settings.url,
        supabase_publishable_key=settings.publishable_key,
        code=str(code)[:2_000],
        flow_id=str(flow_id)[:64],
        default=None,
        key=key,
    )
    return value if isinstance(value, dict) else None


def clear_google_oauth_artifacts(
    *,
    key: str = "supabase_google_oauth_clear",
) -> None:
    """Remove temporary PKCE state and any duplicate browser client session."""
    _persistence(
        operation="clear_google_oauth",
        namespace="auth",
        default=None,
        key=key,
    )
