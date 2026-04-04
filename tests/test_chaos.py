"""Tests for the /chaos/* endpoints."""


def test_chaos_error_returns_500(client):
    resp = client.get("/chaos/error")
    assert resp.status_code == 500


def test_chaos_error_custom_status(client):
    resp = client.get("/chaos/error?status=503")
    assert resp.status_code == 503


def test_chaos_error_returns_json(client):
    data = client.get("/chaos/error").get_json()
    assert "error" in data


def test_chaos_health_fail_returns_503(client):
    resp = client.get("/chaos/health-fail")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["status"] == "unhealthy"


def test_chaos_error_flood_returns_200(client):
    resp = client.get("/chaos/error-flood?count=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["errors_generated"] == 5


def test_chaos_error_flood_respects_max(client):
    resp = client.get("/chaos/error-flood?count=999")
    data = resp.get_json()
    assert data["errors_generated"] <= 200


def test_chaos_cpu_returns_200(client):
    resp = client.get("/chaos/cpu?duration=1&threads=1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["chaos"] == "cpu_spike"


def test_chaos_latency_returns_200(client):
    resp = client.get("/chaos/latency?delay=1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["delay_seconds"] == 1
