"""Tests for the alert management endpoint."""


def test_create_alert(client):
    resp = client.post("/alerts", json={
        "alert_name": "HighErrorRate",
        "severity": "warning",
        "summary": "Error rate above 10%",
        "source": "prod-nyc",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["alert_name"] == "HighErrorRate"
    assert data["status"] == "firing"
    assert data["severity"] == "warning"
    assert data["source"] == "prod-nyc"


def test_create_alert_missing_name(client):
    resp = client.post("/alerts", json={"severity": "critical"})
    assert resp.status_code == 400


def test_list_alerts(client):
    client.post("/alerts", json={"alert_name": "ServiceDown", "severity": "critical"})
    client.post("/alerts", json={"alert_name": "HighErrorRate", "severity": "warning"})

    resp = client.get("/alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_list_alerts_filter_status(client):
    client.post("/alerts", json={"alert_name": "ServiceDown"})
    client.post("/alerts", json={"alert_name": "HighErrorRate"})

    # Acknowledge one
    alerts = client.get("/alerts").get_json()
    client.put(f"/alerts/{alerts[0]['id']}", json={"status": "acknowledged"})

    resp = client.get("/alerts?status=firing")
    assert len(resp.get_json()) == 1


def test_list_alerts_filter_severity(client):
    client.post("/alerts", json={"alert_name": "A", "severity": "critical"})
    client.post("/alerts", json={"alert_name": "B", "severity": "warning"})

    resp = client.get("/alerts?severity=critical")
    assert len(resp.get_json()) == 1


def test_get_alert(client):
    resp = client.post("/alerts", json={"alert_name": "Test"})
    alert_id = resp.get_json()["id"]

    resp = client.get(f"/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.get_json()["alert_name"] == "Test"


def test_get_alert_not_found(client):
    resp = client.get("/alerts/9999")
    assert resp.status_code == 404


def test_acknowledge_alert(client):
    resp = client.post("/alerts", json={"alert_name": "ServiceDown"})
    alert_id = resp.get_json()["id"]

    resp = client.put(f"/alerts/{alert_id}", json={
        "status": "acknowledged",
        "acknowledged_by": "austin",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by"] == "austin"
    assert data["acknowledged_at"] is not None


def test_resolve_alert(client):
    resp = client.post("/alerts", json={"alert_name": "ServiceDown"})
    alert_id = resp.get_json()["id"]

    resp = client.put(f"/alerts/{alert_id}", json={"status": "resolved"})
    data = resp.get_json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


def test_add_notes_to_alert(client):
    resp = client.post("/alerts", json={"alert_name": "ServiceDown"})
    alert_id = resp.get_json()["id"]

    client.put(f"/alerts/{alert_id}", json={"notes": "Investigating DB connection"})
    client.put(f"/alerts/{alert_id}", json={"notes": "Found root cause: DNS timeout"})

    resp = client.get(f"/alerts/{alert_id}")
    data = resp.get_json()
    assert "Investigating DB connection" in data["notes"]
    assert "Found root cause: DNS timeout" in data["notes"]


def test_invalid_status_update(client):
    resp = client.post("/alerts", json={"alert_name": "Test"})
    alert_id = resp.get_json()["id"]

    resp = client.put(f"/alerts/{alert_id}", json={"status": "invalid"})
    assert resp.status_code == 400
