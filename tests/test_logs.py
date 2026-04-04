"""Tests for the /logs endpoint."""
import json
import tempfile
import os


def test_logs_returns_200(client):
    resp = client.get("/logs")
    assert resp.status_code == 200


def test_logs_returns_structure(client):
    data = client.get("/logs").get_json()
    assert "logs" in data
    assert "count" in data
    assert isinstance(data["logs"], list)


def test_logs_respects_limit(client):
    data = client.get("/logs?limit=5").get_json()
    assert data["count"] <= 5


def test_logs_filters_by_level(client):
    data = client.get("/logs?level=ERROR").get_json()
    for log in data["logs"]:
        assert log.get("level") == "ERROR"
