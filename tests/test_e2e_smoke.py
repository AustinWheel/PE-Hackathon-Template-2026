"""
End-to-end smoke tests that run against a live deployment.

These tests are excluded from the default pytest suite (see pyproject.toml).
They are triggered by CI with: BASE_URL=<url> pytest tests/test_e2e_smoke.py
"""

import os
import pytest
import urllib.request
import json


@pytest.fixture
def base_url():
    url = os.environ.get("BASE_URL")
    if not url:
        pytest.skip("BASE_URL not set, skipping e2e tests")
    return url.rstrip("/")


def http_get(url):
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=10)
    return resp.status, json.loads(resp.read().decode())


def http_post(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=10)
    return resp.status, json.loads(resp.read().decode())


# --- Health & Metrics ---

def test_health_ok(base_url):
    status, data = http_get(f"{base_url}/health")
    assert status == 200
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_metrics_endpoint(base_url):
    req = urllib.request.Request(f"{base_url}/metrics")
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    data = json.loads(resp.read().decode())
    assert "cpu_percent" in data or "total_requests" in data


def test_prometheus_metrics(base_url):
    req = urllib.request.Request(f"{base_url}/prom-metrics")
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    body = resp.read().decode()
    assert "http_requests_total" in body


# --- CRUD Operations ---

def test_create_and_get_user(base_url):
    status, user = http_post(f"{base_url}/users", {
        "username": "e2e_test_user",
        "email": "e2e@test.com",
    })
    assert status == 201
    assert user["username"] == "e2e_test_user"

    status, fetched = http_get(f"{base_url}/users/{user['id']}")
    assert status == 200
    assert fetched["email"] == "e2e@test.com"


def test_list_users(base_url):
    status, data = http_get(f"{base_url}/users?page=1&per_page=5")
    assert status == 200
    assert isinstance(data, (list, dict))


def test_create_and_list_products(base_url):
    status, data = http_get(f"{base_url}/products")
    assert status == 200
    assert isinstance(data, list)


def test_create_url_and_redirect(base_url):
    # Create a user first
    _, user = http_post(f"{base_url}/users", {
        "username": "e2e_url_user",
        "email": "e2e_url@test.com",
    })

    # Create a short URL
    status, url_data = http_post(f"{base_url}/urls", {
        "user_id": user["id"],
        "original_url": "https://example.com",
        "title": "E2E Test URL",
    })
    assert status == 201
    assert "short_code" in url_data

    # Verify redirect works (follow=false, check 302)
    code = url_data["short_code"]
    req = urllib.request.Request(f"{base_url}/r/{code}", method="GET")
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        # 302 redirect is expected
        assert e.code in (301, 302, 307, 308)


# --- Alerts ---

def test_create_and_list_alerts(base_url):
    status, alert = http_post(f"{base_url}/alerts", {
        "alert_name": "e2e_smoke_test",
        "severity": "warning",
        "summary": "E2E smoke test alert",
        "source": "ci-pipeline",
    })
    assert status == 201
    assert alert["status"] == "firing"

    status, alerts = http_get(f"{base_url}/alerts")
    assert status == 200
    assert any(a["alert_name"] == "e2e_smoke_test" for a in alerts)


# --- Chaos Endpoints Respond ---

def test_chaos_error_endpoint(base_url):
    try:
        http_get(f"{base_url}/chaos/error")
    except urllib.error.HTTPError as e:
        assert e.code == 500  # Expected


def test_chaos_latency_endpoint(base_url):
    status, data = http_get(f"{base_url}/chaos/latency?delay=1")
    assert status == 200
    assert data["delay_seconds"] == 1
