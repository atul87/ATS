import shutil

import pytest


def test_root_endpoint_lists_primary_routes(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ATS Resume Analyzer API"
    assert "POST   /api/v1/analyze-resume" in body["endpoints"]


def test_health_endpoint_reports_loaded_test_models(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "nlp_loaded": True,
        "embedder_loaded": True,
    }


@pytest.mark.skipif(
    shutil.which("tesseract") is None or shutil.which("pdftoppm") is None,
    reason="OCR runtime binaries are not installed in this environment",
)
def test_ocr_dependencies_present():
    assert shutil.which("tesseract")
    assert shutil.which("pdftoppm")


def test_version_root_and_api_v1(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "0.9.0-beta")
    monkeypatch.setenv("ENVIRONMENT", "preprod")
    monkeypatch.setenv("COMMIT_SHA", "46b41b9")

    for path in ("/version", "/api/v1/version"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert body["version"] == "0.9.0-beta"
        assert body["environment"] == "preprod"
        assert body["commit"] == "46b41b9"


def test_build_root_and_api_v1(client, monkeypatch):
    monkeypatch.setenv("BUILD_TIME", "2026-05-23T12:45:00Z")
    monkeypatch.setenv("ENVIRONMENT", "preprod")
    monkeypatch.setenv("ATS_FAST_MODEL_MODE", "true")

    for path in ("/build", "/api/v1/build"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert body["build_time"] == "2026-05-23T12:45:00Z"
        assert body["environment"] == "preprod"
        assert body["fast_mode"] is True


def test_commit_root_and_api_v1(client, monkeypatch):
    monkeypatch.setenv("COMMIT_SHA", "46b41b9")

    for path in ("/commit", "/api/v1/commit"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert body["commit"] == "46b41b9"
        assert body["source"] == "env"


def test_version_fallback_behavior(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)

    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.9.0-beta"  # fallback default
    assert body["environment"] == "development"  # fallback default
    assert isinstance(body["commit"], str)
    assert len(body["commit"]) > 0


def test_version_env_override(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "1.2.3"
