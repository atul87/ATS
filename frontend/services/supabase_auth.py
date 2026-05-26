import os
import logging
from pathlib import Path
from typing import Any, Dict
import streamlit as st
from supabase import Client, create_client
from frontend.services.auth_provider import AuthProvider

logger = logging.getLogger("ats_resume_scorer")

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


def _secret(key: str, section: str = "supabase") -> str:
    """Read from env first, then fall back to st.secrets[section][key]."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        return st.secrets[section][key]
    except Exception:
        return ""


SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_ANON_KEY = _secret("SUPABASE_ANON_KEY")

OAUTH_REDIRECT_URL = (
    os.getenv("AUTH_REDIRECT_URL")
    or _secret("redirect_uri", "google_oauth")
    or "http://localhost:8501"
)


class SupabaseAuthProvider(AuthProvider):
    def _missing_config(self) -> str | None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            return "Supabase is not configured — set SUPABASE_URL and SUPABASE_ANON_KEY in .env or .streamlit/secrets.toml"
        return None

    def get_client(self) -> Client | None:
        """Helper to instantiate or return a cached client."""
        # Using streamlit's cache_resource to store the client on the class
        if not hasattr(self, "_cached_client"):
            if self._missing_config():
                return None
            self._cached_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return self._cached_client

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
            resp = self.get_client().auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": OAUTH_REDIRECT_URL},
                }
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
            storage_key = f"{client.auth._storage_key}-code-verifier"
            code_verifier = client.auth._storage.get_item(storage_key) or ""
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
            self.get_client().auth.sign_out()
        except Exception as exc:
            logger.warning(f"sign_out failed: {exc}")

    def _humanize(self, exc: Exception) -> str:
        msg = str(exc)
        if "invalid_grant" in msg.lower() or "invalid login" in msg.lower():
            return "Wrong email or password"
        if "user already registered" in msg.lower() or "already been registered" in msg.lower():
            return "An account with this email already exists — try signing in"
        if "password should be at least" in msg.lower():
            return "Password too short (Supabase default is 6 characters)"
        return msg
