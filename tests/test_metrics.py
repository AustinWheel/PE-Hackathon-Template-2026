"""Tests for the /metrics and /prom-metrics endpoints."""


def test_metrics_returns_200(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_returns_cpu(client):
    data = client.get("/metrics").get_json()
    assert "cpu_percent" in data


def test_metrics_returns_memory(client):
    data = client.get("/metrics").get_json()
    assert "memory_percent" in data
    assert "memory_used_mb" in data
    assert "memory_total_mb" in data


def test_metrics_values_are_numbers(client):
    data = client.get("/metrics").get_json()
    assert isinstance(data["cpu_percent"], (int, float))
    assert isinstance(data["memory_percent"], (int, float))


def test_prom_metrics_returns_200(client):
    resp = client.get("/prom-metrics")
    assert resp.status_code == 200


def test_prom_metrics_returns_text_format(client):
    resp = client.get("/prom-metrics")
    content_type = resp.content_type
    assert "text/plain" in content_type or "text/openmetrics" in content_type


def test_prom_metrics_contains_counters(client):
    resp = client.get("/prom-metrics")
    body = resp.data.decode()
    assert "http_requests_total" in body
    assert "app_up" in body
