import base64
import json
import os
from types import SimpleNamespace

import pytest

os.environ["MOCK_AUTH"] = "true"

from frontend.services import supabase_auth


def _jwt_with_role(role: str) -> str:
    def encode(data):
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode({'role': role})}.sig"


@pytest.fixture(autouse=True)
def clean_supabase_config(monkeypatch):
    for key in (
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_PUBLISHABLE_KEY",
        "AUTH_REDIRECT_URL",
        "APP_BASE_URL",
        "url",
        "anon_key",
        "publishable_key",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(supabase_auth.st, "secrets", {})


def test_reads_top_level_streamlit_supabase_secrets(monkeypatch):
    monkeypatch.setattr(
        supabase_auth.st,
        "secrets",
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "sb_publishable_test",
        },
    )

    assert supabase_auth._supabase_url() == "https://example.supabase.co"
    assert supabase_auth._supabase_api_key() == "sb_publishable_test"


def test_reads_nested_streamlit_supabase_secrets(monkeypatch):
    monkeypatch.setattr(
        supabase_auth.st,
        "secrets",
        {
            "supabase": {
                "url": "https://nested.supabase.co",
                "anon_key": "sb_publishable_nested",
            }
        },
    )

    assert supabase_auth._supabase_url() == "https://nested.supabase.co"
    assert supabase_auth._supabase_api_key() == "sb_publishable_nested"


def test_reads_publishable_key_from_environment(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "Bearer sb_publishable_env")

    assert supabase_auth._supabase_url() == "https://env.supabase.co"
    assert supabase_auth._supabase_api_key() == "sb_publishable_env"


def test_auth_redirect_reads_top_level_streamlit_secret(monkeypatch):
    monkeypatch.setattr(
        supabase_auth.st,
        "secrets",
        {"AUTH_REDIRECT_URL": "https://app.example.com"},
    )

    assert supabase_auth._auth_redirect_url() == "https://app.example.com"


def test_auth_redirect_reads_nested_google_oauth_secret(monkeypatch):
    monkeypatch.setattr(
        supabase_auth.st,
        "secrets",
        {"google_oauth": {"redirect_uri": "https://nested.example.com"}},
    )

    assert supabase_auth._auth_redirect_url() == "https://nested.example.com"


def test_rejects_frontend_service_role_key():
    err = supabase_auth._validate_config(
        "https://example.supabase.co",
        _jwt_with_role("service_role"),
    )

    assert "service_role" in err


def test_accepts_legacy_anon_jwt():
    err = supabase_auth._validate_config(
        "https://example.supabase.co",
        _jwt_with_role("anon"),
    )

    assert err is None


def test_get_client_does_not_cache_auth_state(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_test")
    calls = []

    def fake_create_client(url, api_key, options=None):
        calls.append((url, api_key, options))
        return object()

    monkeypatch.setattr(supabase_auth, "create_client", fake_create_client)

    provider = supabase_auth.SupabaseAuthProvider()
    assert provider.get_client() is not provider.get_client()
    assert len(calls) == 2
    assert calls[0][2].persist_session is False
    assert calls[0][2].auto_refresh_token is False


def test_sign_up_passes_email_redirect_to_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_test")
    monkeypatch.setenv("AUTH_REDIRECT_URL", "https://app.example.com")
    sign_up_calls = []

    class FakeAuth:
        def sign_up(self, payload):
            sign_up_calls.append(payload)
            return SimpleNamespace(session=None, user=SimpleNamespace(id="user-1"))

    class FakeClient:
        auth = FakeAuth()

    monkeypatch.setattr(
        supabase_auth,
        "create_client",
        lambda url, api_key, options=None: FakeClient(),
    )

    result = supabase_auth.SupabaseAuthProvider().sign_up_with_password(
        "test@example.com", "password123"
    )

    assert result == {"pending_confirmation": True, "email": "test@example.com"}
    assert sign_up_calls == [
        {
            "email": "test@example.com",
            "password": "password123",
            "options": {"email_redirect_to": "https://app.example.com"},
        }
    ]
