"""Integration tests for /events endpoint."""


def _seed_data(client):
    """Create a user, URL, and trigger a redirect to generate events."""
    user_resp = client.post("/users", json={"username": "evtuser", "email": "evt@test.com"})
    user_id = user_resp.get_json()["id"]

    url_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    short_code = url_resp.get_json()["short_code"]

    # Trigger a click event
    client.get(f"/r/{short_code}")

    return user_id


def test_list_events_empty(client):
    resp = client.get("/events")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_events_after_url_creation(client):
    _seed_data(client)
    resp = client.get("/events")
    assert resp.status_code == 200
    events = resp.get_json()
    assert len(events) >= 1


def test_events_contain_required_fields(client):
    _seed_data(client)
    events = client.get("/events").get_json()
    for event in events:
        assert "id" in event
        assert "url_id" in event
        assert "user_id" in event
        assert "event_type" in event
        assert "timestamp" in event
        assert "details" in event


def test_events_pagination(client):
    # Create multiple events
    user_resp = client.post("/users", json={"username": "paguser", "email": "pag@test.com"})
    user_id = user_resp.get_json()["id"]

    for i in range(5):
        url_resp = client.post("/urls", json={"original_url": f"https://{i}.com", "user_id": user_id})
        short_code = url_resp.get_json()["short_code"]
        client.get(f"/r/{short_code}")

    # 5 "created" events + 5 "click" events = 10 total
    resp = client.get("/events?page=1&per_page=3")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3


def test_event_types_are_correct(client):
    _seed_data(client)
    events = client.get("/events").get_json()
    event_types = {e["event_type"] for e in events}
    assert event_types.issubset({"created", "click"})
