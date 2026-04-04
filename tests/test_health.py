"""Tests for the /health endpoint."""


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_returns_ok_status(client):
    data = client.get("/health").get_json()
    assert data["status"] == "ok"


def test_health_includes_version(client):
    data = client.get("/health").get_json()
    assert "version" in data


def test_health_includes_uptime(client):
    data = client.get("/health").get_json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_health_includes_database_status(client):
    data = client.get("/health").get_json()
    assert "database" in data
    assert data["database"] == "connected"
