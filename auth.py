"""Optional Google OAuth authentication for HireSense AI.

Authentication is disabled by default for local use. When enabled, Google
OAuth callbacks and persisted browser sessions are protected with short-lived
HMAC-signed tokens. User identity is never accepted directly from URL fields.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse

import requests
import streamlit as st


def _secret(name: str, default: str = "") -> str:
    """Read an optional Streamlit secret without requiring a secrets file."""
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _setting(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or _secret(name, default).strip()


def auth_required() -> bool:
    """Return whether this deployment requires Google sign-in."""
    return _setting("HIRESENSE_AUTH_REQUIRED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _get_client_id() -> str:
    return _setting("GOOGLE_CLIENT_ID")


def _get_client_secret() -> str:
    return _setting("GOOGLE_CLIENT_SECRET")


def _get_redirect_uri() -> str:
    return _setting("GOOGLE_REDIRECT_URI", "http://localhost:8501/")


def _get_session_secret() -> str:
    return _setting("HIRESENSE_SESSION_SECRET")


def auth_is_configured() -> bool:
    """Return whether every setting required for secure OAuth is present."""
    return bool(
        _get_client_id()
        and _get_client_secret()
        and _get_redirect_uri()
        and _get_session_secret()
    )


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_payload(payload: dict) -> str:
    """Return a compact HMAC-signed JSON token."""
    encoded = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signature = hmac.new(
        _get_session_secret().encode(),
        encoded.encode(),
        hashlib.sha256,
    ).digest()
    return f"{encoded}.{_b64encode(signature)}"


def _verify_token(token: str, purpose: str) -> dict | None:
    """Validate signature, purpose, and expiry for a signed token."""
    if not token or not _get_session_secret():
        return None
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = _b64encode(
            hmac.new(
                _get_session_secret().encode(),
                encoded.encode(),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        payload = json.loads(_b64decode(encoded))
        if payload.get("purpose") != purpose:
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def create_session_token(user_info: dict, ttl_seconds: int = 43_200) -> str:
    """Create a signed browser-session token for a verified Google profile."""
    now = int(time.time())
    return _sign_payload(
        {
            "purpose": "session",
            "iat": now,
            "exp": now + ttl_seconds,
            "uid": str(user_info.get("uid", "")),
            "email": str(user_info.get("email", "")),
            "display_name": str(user_info.get("display_name") or "HireSense User"),
            "photo_url": str(user_info.get("photo_url", "")),
        }
    )


def verify_session_token(token: str) -> dict | None:
    """Return a verified profile from a signed session token."""
    payload = _verify_token(token, "session")
    if not payload or not payload.get("uid"):
        return None
    return {
        "uid": payload["uid"],
        "email": payload.get("email", ""),
        "display_name": payload.get("display_name", "HireSense User"),
        "photo_url": payload.get("photo_url", ""),
    }


def _new_oauth_state() -> str:
    now = int(time.time())
    return _sign_payload(
        {
            "purpose": "oauth_state",
            "nonce": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + 600,
        }
    )


def _build_oauth_url() -> str:
    params = {
        "client_id": _get_client_id(),
        "redirect_uri": _get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "select_account",
        "state": _new_oauth_state(),
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        params
    )


def _exchange_code_for_user(code: str) -> dict | None:
    """Exchange a Google authorization code for a verified user profile."""
    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": _get_client_id(),
                "client_secret": _get_client_secret(),
                "redirect_uri": _get_redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            return None

        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        user_response.raise_for_status()
        data = user_response.json()
        if not data.get("sub"):
            return None
        return {
            "uid": data["sub"],
            "email": data.get("email", ""),
            "display_name": data.get("name") or "HireSense User",
            "photo_url": data.get("picture", ""),
        }
    except (requests.RequestException, ValueError):
        return None


def _restore_profile(user_info: dict) -> None:
    st.session_state["logged_in"] = True
    st.session_state["uid"] = user_info["uid"]
    st.session_state["email"] = user_info.get("email", "")
    st.session_state["display_name"] = user_info.get("display_name", "HireSense User")
    st.session_state["photo_url"] = user_info.get("photo_url", "")


def _get_save_auth_html(token: str) -> str:
    """Return JavaScript that persists only a signed session token."""
    token_json = json.dumps(token)
    return f"""
    <script>
    localStorage.setItem("hiresense_auth_token", {token_json});
    localStorage.removeItem("hiresense_auth");
    </script>
    """


def _get_clear_auth_html() -> str:
    """Return JavaScript that clears current and legacy auth storage."""
    return """
    <script>
    localStorage.removeItem("hiresense_auth_token");
    localStorage.removeItem("hiresense_auth");
    </script>
    """


def _render_session_restore_script() -> None:
    st.iframe(
        """
        <script>
        (() => {
          const token = localStorage.getItem("hiresense_auth_token");
          const params = new URLSearchParams(window.parent.location.search);
          if (token && !params.has("code") && !params.has("auth_token")) {
            const base = window.parent.location.origin +
                         window.parent.location.pathname;
            window.parent.location.replace(
              base + "?auth_token=" + encodeURIComponent(token)
            );
          }
        })();
        </script>
        """,
        height=0,
    )


def render_login_screen() -> None:
    """Render the login gate and handle verified OAuth/session callbacks."""
    if not auth_is_configured():
        st.error("Google sign-in is enabled but is not fully configured.")
        st.info(
            "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
            "GOOGLE_REDIRECT_URI, and HIRESENSE_SESSION_SECRET. "
            "For local use, set HIRESENSE_AUTH_REQUIRED=false."
        )
        return

    session_token = str(st.query_params.get("auth_token", ""))
    if session_token:
        st.query_params.clear()
        profile = verify_session_token(session_token)
        if profile:
            _restore_profile(profile)
            st.rerun()
        st.iframe(_get_clear_auth_html(), height=0)
        st.warning("Your saved sign-in expired or could not be verified.")

    code = str(st.query_params.get("code", ""))
    state = str(st.query_params.get("state", ""))
    if code:
        st.query_params.clear()
        if not _verify_token(state, "oauth_state"):
            st.error("The sign-in callback could not be verified. Please try again.")
        else:
            with st.spinner("Verifying your Google account..."):
                profile = _exchange_code_for_user(code)
            if profile:
                _restore_profile(profile)
                st.session_state["_save_auth_token_pending"] = create_session_token(
                    profile
                )
                st.rerun()
            st.error("Google sign-in failed. Please try again.")

    _render_session_restore_script()
    from ui_theme import render_brand

    render_brand()
    st.title("Welcome to HireSense AI")
    st.caption("Sign in to open your interview practice workspace.")
    st.link_button(
        "Continue with Google",
        _build_oauth_url(),
        type="primary",
        width="stretch",
    )
    st.caption("Authentication is used only to identify your practice session.")
