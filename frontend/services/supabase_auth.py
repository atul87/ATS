import logging
import os
import base64
import json
from pathlib import Path
from typing import Any, Dict
import streamlit as st
from supabase import Client, ClientOptions, create_client
from frontend.services.auth_provider import AuthProvider

logger = logging.getLogger("ats_resume_scorer")

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


def _clean_secret(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().strip('"').strip("'").strip()
    if text.lower().startswith("bearer "):
        text = text[7:].strip()
    return text


def _streamlit_secret(key: str) -> str:
    try:
        return _clean_secret(st.secrets.get(key, ""))
    except Exception:
        return ""


def _nested_streamlit_secret(section: str, key: str) -> str:
    try:
        section_values = st.secrets.get(section, {})
        getter = getattr(section_values, "get", None)
        if getter:
            return _clean_secret(getter(key, ""))
        return _clean_secret(section_values[key])
    except Exception:
        return ""


def _secret(
    *keys: str,
    section: str = "supabase",
    nested_keys: tuple[str, ...] = (),
) -> str:
    """Read env, top-level Streamlit secrets, then nested Streamlit secrets."""
    for key in keys:
        value = _clean_secret(os.getenv(key, ""))
        if value:
            return value

    for key in keys:
        value = _streamlit_secret(key)
        if value:
            return value

    for key in (*keys, *nested_keys):
        value = _nested_streamlit_secret(section, key)
        if value:
            return value

    return ""


def _supabase_url() -> str:
    return _secret("SUPABASE_URL", nested_keys=("url",))


def _supabase_api_key() -> str:
    return _secret(
        "SUPABASE_ANON_KEY",
        "SUPABASE_PUBLISHABLE_KEY",
        nested_keys=("anon_key", "publishable_key"),
    )


OAUTH_REDIRECT_URL = (
    os.getenv("AUTH_REDIRECT_URL")
    or _secret("redirect_uri", section="google_oauth")
    or "http://localhost:8501"
)


def _jwt_payload(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


def _validate_config(url: str, api_key: str) -> str | None:
    if not url or not api_key:
        return (
            "Supabase is not configured - set SUPABASE_URL and "
            "SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY in Streamlit secrets"
        )

    if not url.startswith(("http://", "https://")):
        return "Supabase URL must start with http:// or https://"

    lowered_key = api_key.lower()
    if (
        "your_" in lowered_key
        or "paste_" in lowered_key
        or "replace_" in lowered_key
        or api_key == "..."
    ):
        return "Supabase API key is still a placeholder - paste the real anon or publishable key"

    if api_key.startswith("sb_secret_"):
        return "Use a Supabase publishable or anon key for the frontend, not an sb_secret key"

    role = _jwt_payload(api_key).get("role")
    if role == "service_role":
        return "Use SUPABASE_ANON_KEY in Streamlit, not the backend service_role key"
    if role and role != "anon":
        return f"Frontend Supabase key must have anon role, not {role}"

    if not (api_key.startswith("sb_publishable_") or role == "anon"):
        return "Supabase API key must be an sb_publishable_ key or legacy anon JWT"

    return None


class SupabaseAuthProvider(AuthProvider):
    def _missing_config(self) -> str | None:
        return _validate_config(_supabase_url(), _supabase_api_key())

    def get_client(self) -> Client | None:
        """Create a short-lived client so auth state is not shared across users."""
        url = _supabase_url()
        api_key = _supabase_api_key()
        if _validate_config(url, api_key):
            return None
        options = ClientOptions(auto_refresh_token=False, persist_session=False)
        return create_client(url, api_key, options=options)

    def _session_dict(self, session, user) -> Dict[str, Any]:
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "email": user.email,
        }

    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        err = self._missing_config()
        if err:
            return {"error": err}
        try:
            resp = self.get_client().auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            if not resp.session or not resp.user:
                return {"error": "Invalid credentials"}
            return self._session_dict(resp.session, resp.user)
        except Exception as exc:
            logger.warning(f"sign_in_with_password failed: {exc}")
            return {"error": self._humanize(exc)}

    def sign_up_with_password(self, email: str, password: str) -> Dict[str, Any]:
        err = self._missing_config()
        if err:
            return {"error": err}
        try:
            resp = self.get_client().auth.sign_up({"email": email, "password": password})
            if resp.session and resp.user:
                return self._session_dict(resp.session, resp.user)
            if resp.user:
                return {"pending_confirmation": True, "email": email}
            return {"error": "Sign-up failed"}
        except Exception as exc:
            logger.warning(f"sign_up failed: {exc}")
            return {"error": self._humanize(exc)}

    def google_oauth_url(self) -> Dict[str, Any]:
        err = self._missing_config()
        if err:
            return {"error": err}
        try:
            client = self.get_client()
            resp = client.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": OAUTH_REDIRECT_URL},
                }
            )
            storage_key = f"{client.auth._storage_key}-code-verifier"
            st.session_state["oauth_code_verifier"] = (
                client.auth._storage.get_item(storage_key) or ""
            )
            return {"url": resp.url}
        except Exception as exc:
            logger.warning(f"oauth url generation failed: {exc}")
            return {"error": self._humanize(exc)}

    def exchange_code_for_session(self, auth_code: str) -> Dict[str, Any]:
        """Called once after the OAuth provider redirects back with `?code=...`."""
        err = self._missing_config()
        if err:
            return {"error": err}
        client = self.get_client()
        try:
            code_verifier = st.session_state.pop("oauth_code_verifier", "")
            resp = client.auth.exchange_code_for_session(
                {
                    "auth_code": auth_code,
                    "code_verifier": code_verifier,
                    "redirect_to": OAUTH_REDIRECT_URL,
                }
            )
            if not resp.session or not resp.user:
                return {"error": "OAuth exchange returned no session"}
            return self._session_dict(resp.session, resp.user)
        except Exception as exc:
            logger.warning(f"exchange_code_for_session failed: {exc}")
            return {"error": self._humanize(exc)}

    def sign_out(self) -> None:
        if self._missing_config():
            return
        try:
            access_token = st.session_state.get("access_token")
            if access_token:
                self.get_client().auth.admin.sign_out(access_token)
            else:
                self.get_client().auth.sign_out()
        except Exception as exc:
            logger.warning(f"sign_out failed: {exc}")

    def _humanize(self, exc: Exception) -> str:
        msg = str(exc)
        if "invalid api key" in msg.lower() or "api key is invalid" in msg.lower():
            return "Invalid Supabase API key - use the project's publishable or anon key"
        if "invalid_grant" in msg.lower() or "invalid login" in msg.lower():
            return "Wrong email or password"
        if "user already registered" in msg.lower() or "already been registered" in msg.lower():
            return "An account with this email already exists — try signing in"
        if "password should be at least" in msg.lower():
            return "Password too short (Supabase default is 6 characters)"
        return msg
