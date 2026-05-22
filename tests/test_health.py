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
