import backend.core.config as config


def test_required_env_accepts_documented_supabase_service_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "server-only-key")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert config.check_required_env_vars() == []


def test_required_env_accepts_legacy_supabase_key_alias(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_KEY", "legacy-server-only-key")

    assert config.check_required_env_vars() == []


def test_required_env_reports_canonical_supabase_service_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    assert config.check_required_env_vars() == ["SUPABASE_SERVICE_KEY"]


def test_allowed_origins_do_not_include_trailing_slashes():
    assert config.ALLOWED_ORIGINS
    assert all(not origin.endswith("/") for origin in config.ALLOWED_ORIGINS)
