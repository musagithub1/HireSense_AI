"""Supabase Auth gate for RLS-protected HireSense data."""

from __future__ import annotations

import math
import re
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import streamlit as st

import persistence_component as persistence
from supabase_backend import (
    SupabaseError,
    SupabaseGateway,
    boolean_setting,
    is_configured,
    setting,
)

_OAUTH_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._~+/=-]{8,2000}$")
_OAUTH_FLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_OAUTH_QUERY_KEYS = {
    "code",
    "sb_flow_id",
    "error",
    "error_code",
    "error_description",
}


def auth_required() -> bool:
    """Use Supabase Auth by default whenever Supabase is configured."""
    return is_configured() and boolean_setting(
        "HIRESENSE_SUPABASE_AUTH_REQUIRED",
        default=True,
    )


def google_auth_enabled() -> bool:
    """Show Google sign-in when Supabase Auth is active unless disabled."""
    return auth_required() and boolean_setting(
        "HIRESENSE_GOOGLE_AUTH_ENABLED",
        default=True,
    )


def _oauth_redirect_url() -> str:
    """Return an optional, validated OAuth destination override."""
    raw = (
        setting("SUPABASE_OAUTH_REDIRECT_URL")
        or setting("HIRESENSE_PUBLIC_URL")
        or setting("REDIRECT_URI")
    ).strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return ""
    local_http = parsed.scheme == "http" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if (
        (parsed.scheme != "https" and not local_http)
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return ""
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            "",
            "",
        )
    )


def _query_value(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        value = value[-1] if value else ""
    return str(value).strip()


def _clear_oauth_query_params() -> None:
    """Remove OAuth callback fields while retaining unrelated app parameters."""
    current = st.query_params.to_dict()
    cleaned = {
        key: value for key, value in current.items() if key not in _OAUTH_QUERY_KEYS
    }
    st.query_params.from_dict(cleaned)


def _valid_supabase_user_id(value: Any) -> bool:
    try:
        UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def _session_from_response(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize GoTrue sign-in, sign-up, and refresh responses."""
    source = payload.get("session")
    if not isinstance(source, dict):
        source = payload
    access_token = str(source.get("access_token", "")).strip()
    refresh_token = str(source.get("refresh_token", "")).strip()
    if (
        not access_token
        or not refresh_token
        or len(access_token) > 16_000
        or len(refresh_token) > 16_000
    ):
        return None

    expires_at = source.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        expires_in = source.get("expires_in", 3600)
        try:
            expires_at = time.time() + float(expires_in)
        except (TypeError, ValueError):
            expires_at = time.time() + 3600
    try:
        expires_at = float(expires_at)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(expires_at) or expires_at <= 0:
        return None

    user = payload.get("user")
    if not isinstance(user, dict):
        user = source.get("user")
    user = user if isinstance(user, dict) else {}
    if user.get("id") and not _valid_supabase_user_id(user.get("id")):
        return None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "user": user,
    }


def _apply_session(session: dict[str, Any]) -> bool:
    user = session.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        try:
            user = SupabaseGateway.configured(
                access_token=str(session["access_token"])
            ).get_user()
        except (SupabaseError, KeyError):
            return False
    if not user.get("id") or not _valid_supabase_user_id(user.get("id")):
        return False

    metadata = user.get("user_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    email = str(user.get("email", ""))[:320]
    full_name = str(
        metadata.get("full_name")
        or metadata.get("name")
        or email.split("@", 1)[0]
        or "HireSense User"
    )[:200]
    previous_uid = st.session_state.get("uid")
    if previous_uid and str(previous_uid) != str(user["id"]):
        _clear_private_workspace()
    st.session_state["logged_in"] = True
    st.session_state["uid"] = str(user["id"])
    st.session_state["email"] = email
    st.session_state["display_name"] = full_name
    st.session_state["photo_url"] = str(
        metadata.get("avatar_url") or metadata.get("picture") or ""
    )[:2_000]
    st.session_state["supabase_access_token"] = str(session["access_token"])
    st.session_state["supabase_refresh_token"] = str(session["refresh_token"])
    st.session_state["supabase_expires_at"] = float(session["expires_at"])
    app_metadata = user.get("app_metadata")
    app_metadata = app_metadata if isinstance(app_metadata, dict) else {}
    st.session_state["auth_provider"] = str(
        app_metadata.get("provider") or "supabase"
    )
    st.session_state["_save_supabase_session_pending"] = {
        "access_token": str(session["access_token"]),
        "refresh_token": str(session["refresh_token"]),
        "expires_at": float(session["expires_at"]),
    }
    st.session_state["_supabase_restore_failed"] = False
    return True


def _clear_private_workspace() -> None:
    """Prevent one signed-in user from inheriting another user's session data."""
    reset_values = {
        "interview_started": False,
        "interview_complete": False,
        "interview_resume_text": None,
        "interview_jd_text": None,
        "interview_rag_context": None,
        "interview_history": [],
        "question_bank": [],
        "interview_report": None,
        "evidence_assessment": None,
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
        "_persistence_restored": False,
        "_resume_upload_bytes": None,
        "_resume_upload_name": None,
        "save_resume_file": False,
    }
    for key, value in reset_values.items():
        st.session_state[key] = value


def _clear_session_state() -> None:
    _clear_private_workspace()
    for key, value in {
        "logged_in": False,
        "uid": None,
        "email": None,
        "display_name": None,
        "photo_url": None,
        "auth_provider": None,
        "supabase_access_token": None,
        "supabase_refresh_token": None,
        "supabase_expires_at": None,
        "_database_restored": False,
        "_recoverable_interview_loaded": False,
    }.items():
        st.session_state[key] = value


def restore_persisted_session() -> bool:
    """Restore and rotate a browser-held refresh token once per app session."""
    if st.session_state.get("logged_in") and st.session_state.get(
        "supabase_access_token"
    ):
        return True
    if st.session_state.get("_supabase_restore_failed"):
        return False

    saved = persistence.load_supabase_session()
    if not saved:
        return False
    refresh_token = str(saved.get("refresh_token", "")).strip()
    if not refresh_token:
        return False

    try:
        response = SupabaseGateway.configured().refresh_session(refresh_token)
        session = _session_from_response(response)
        if session and _apply_session(session):
            return True
    except SupabaseError:
        pass

    st.session_state["_supabase_restore_failed"] = True
    st.session_state["_clear_supabase_session_pending"] = True
    _clear_session_state()
    return False


def _process_google_oauth_callback() -> tuple[str, str]:
    """Exchange a browser PKCE callback and apply the resulting Supabase JWT."""
    oauth_error = _query_value("error") or _query_value("error_code")
    if oauth_error:
        _clear_oauth_query_params()
        persistence.clear_google_oauth_artifacts(
            key=f"clear_failed_google_oauth_{int(time.time())}"
        )
        return (
            "error",
            "Google sign-in was cancelled or could not be completed. Please try again.",
        )

    code = _query_value("code")
    if not code:
        return "none", ""
    flow_id = _query_value("sb_flow_id")
    if not _OAUTH_CODE_PATTERN.fullmatch(code) or (
        flow_id and not _OAUTH_FLOW_ID_PATTERN.fullmatch(flow_id)
    ):
        _clear_oauth_query_params()
        persistence.clear_google_oauth_artifacts(
            key=f"clear_invalid_google_oauth_{int(time.time())}"
        )
        return "error", "The Google sign-in callback was invalid. Please try again."

    result = persistence.exchange_google_oauth_code(
        code,
        flow_id=flow_id,
        key=f"exchange_google_oauth_{flow_id or code[:24]}",
    )
    if result is None:
        return "pending", ""
    if result.get("status") != "authenticated":
        _clear_oauth_query_params()
        persistence.clear_google_oauth_artifacts(
            key=f"clear_rejected_google_oauth_{int(time.time())}"
        )
        return (
            "error",
            "Google sign-in could not be verified. Please try again or use email.",
        )

    raw_session = result.get("session")
    session = (
        _session_from_response(raw_session)
        if isinstance(raw_session, dict)
        else None
    )
    if not session or not _apply_session(session):
        _clear_oauth_query_params()
        persistence.clear_google_oauth_artifacts(
            key=f"clear_unverified_google_oauth_{int(time.time())}"
        )
        return (
            "error",
            "Supabase did not return a valid Google session. Please try again.",
        )

    _clear_oauth_query_params()
    return "authenticated", ""


def refresh_if_needed() -> bool:
    """Refresh the user's access token before it expires."""
    access_token = str(st.session_state.get("supabase_access_token") or "")
    refresh_token = str(st.session_state.get("supabase_refresh_token") or "")
    if not access_token or not refresh_token:
        return False
    expires_at = float(st.session_state.get("supabase_expires_at") or 0)
    if expires_at > time.time() + 120:
        return True
    try:
        response = SupabaseGateway.configured().refresh_session(refresh_token)
        session = _session_from_response(response)
        return bool(session and _apply_session(session))
    except SupabaseError:
        _clear_session_state()
        st.session_state["_clear_supabase_session_pending"] = True
        return False


def render_login_screen() -> None:
    """Render Google and email authentication backed by Supabase Auth."""
    if not is_configured():
        st.error(
            "Supabase Auth is enabled but SUPABASE_URL and the public key "
            "are missing."
        )
        return
    from ui_theme import render_brand

    render_brand()
    st.title("Welcome to HireSense AI")
    st.caption(
        "Sign in to start a live voice interview and keep your feedback private."
    )

    callback_status, callback_message = _process_google_oauth_callback()
    if callback_status == "authenticated":
        st.rerun()
    if callback_status == "pending":
        st.info("Completing your secure Google sign-in…")
        return
    if callback_status == "error":
        st.error(callback_message)

    if restore_persisted_session():
        st.rerun()

    if google_auth_enabled():
        google_consent = st.checkbox(
            "I agree to save my interview data in my private account.",
            key="supabase_google_data_consent",
        )
        if google_consent:
            google_result = persistence.render_google_oauth_button(
                redirect_to=_oauth_redirect_url(),
                key="supabase_google_oauth_button",
            )
            if google_result and google_result.get("status") == "error":
                st.error(
                    "Google sign-in could not start. Check the Supabase Google "
                    "provider and redirect URL settings."
                )
        else:
            st.caption("Confirm private data storage to continue with Google.")
        st.divider()
        st.caption("Or use email and password")

    sign_in_tab, create_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("supabase_sign_in_form"):
            email = st.text_input("Email", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                "Sign in",
                type="primary",
                width="stretch",
            )
        if submitted:
            if not email.strip() or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    response = SupabaseGateway.configured().sign_in_with_password(
                        email.strip(),
                        password,
                    )
                    session = _session_from_response(response)
                    if not session or not _apply_session(session):
                        st.error("Supabase did not return a valid session.")
                    else:
                        st.rerun()
                except SupabaseError as exc:
                    st.error(str(exc))

    with create_tab:
        with st.form("supabase_sign_up_form"):
            full_name = st.text_input("Full name", autocomplete="name")
            new_email = st.text_input(
                "Email",
                key="supabase_signup_email",
                autocomplete="email",
            )
            new_password = st.text_input(
                "Password",
                type="password",
                key="supabase_signup_password",
                autocomplete="new-password",
                help="Use at least 8 characters.",
            )
            accepted = st.checkbox(
                "I agree to save my interview data in my private account."
            )
            created = st.form_submit_button(
                "Create candidate account",
                type="primary",
                width="stretch",
            )
        if created:
            if not full_name.strip() or not new_email.strip():
                st.warning("Enter your name and email.")
            elif len(new_password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif not accepted:
                st.warning("Confirm data storage before creating the account.")
            else:
                try:
                    response = SupabaseGateway.configured().sign_up(
                        new_email.strip(),
                        new_password,
                        full_name=full_name.strip(),
                    )
                    session = _session_from_response(response)
                    if session and _apply_session(session):
                        st.rerun()
                    st.success(
                        "Account created. Check your email to confirm it, then sign in."
                    )
                except SupabaseError as exc:
                    st.error(str(exc))

    st.caption(
        "HireSense stores only confirmed transcripts. Partial microphone text is "
        "not written to the database."
    )


def sign_out() -> None:
    token = str(st.session_state.get("supabase_access_token") or "")
    if token:
        try:
            SupabaseGateway.configured(access_token=token).sign_out()
        except SupabaseError:
            pass
    _clear_session_state()
    st.session_state["_clear_supabase_session_pending"] = True
    st.session_state["_clear_supabase_oauth_pending"] = True
