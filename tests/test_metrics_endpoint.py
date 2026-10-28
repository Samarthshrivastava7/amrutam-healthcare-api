from fastapi.testclient import TestClient

import main


def test_metrics_endpoint_is_disabled_without_token(monkeypatch):
    monkeypatch.setattr(main, "METRICS_BEARER_TOKEN", "")
    response = TestClient(main.app).get("/metrics")
    assert response.status_code == 404


def test_metrics_endpoint_requires_bearer_token(monkeypatch):
    monkeypatch.setattr(main, "METRICS_BEARER_TOKEN", "test-metrics-secret")
    client = TestClient(main.app)
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_metrics_endpoint_returns_prometheus_format_with_valid_token(monkeypatch):
    monkeypatch.setattr(main, "METRICS_BEARER_TOKEN", "test-metrics-secret")
    client = TestClient(main.app)
    client.get("/health/live")
    response = client.get(
        "/metrics",
        headers={"Authorization": "Bearer test-metrics-secret"},
    )
    assert response.status_code == 200
    assert "amrutam_http_requests_total" in response.text
    assert "amrutam_http_request_duration_seconds" in response.text
