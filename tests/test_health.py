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
