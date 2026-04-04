"""Integration tests for /urls and /r/<short_code> endpoints."""


def _create_user(client):
    resp = client.post("/users", json={"username": "urluser", "email": "url@test.com"})
    return resp.get_json()["id"]


def test_create_url(client):
    user_id = _create_user(client)
    resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["original_url"] == "https://example.com"
    assert data["is_active"] is True
    assert len(data["short_code"]) == 6
    assert data["user_id"] == user_id


def test_create_url_with_title(client):
    user_id = _create_user(client)
    resp = client.post("/urls", json={
        "original_url": "https://example.com",
        "user_id": user_id,
        "title": "My Link",
    })
    assert resp.status_code == 201
    assert resp.get_json()["title"] == "My Link"


def test_create_url_missing_fields(client):
    resp = client.post("/urls", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_url_missing_user_id(client):
    resp = client.post("/urls", json={"original_url": "https://example.com"})
    assert resp.status_code == 400


def test_create_url_missing_original_url(client):
    user_id = _create_user(client)
    resp = client.post("/urls", json={"user_id": user_id})
    assert resp.status_code == 400


def test_create_url_nonexistent_user(client):
    resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": 99999})
    assert resp.status_code == 404
    assert "User not found" in resp.get_json()["error"]


def test_create_url_generates_event(client):
    user_id = _create_user(client)
    client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})

    events_resp = client.get("/events")
    events = events_resp.get_json()
    assert len(events) == 1
    assert events[0]["event_type"] == "created"


def test_list_urls(client):
    user_id = _create_user(client)
    client.post("/urls", json={"original_url": "https://a.com", "user_id": user_id})
    client.post("/urls", json={"original_url": "https://b.com", "user_id": user_id})

    resp = client.get("/urls")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_urls_filter_by_user(client):
    user_id = _create_user(client)
    resp2 = client.post("/users", json={"username": "other", "email": "other@test.com"})
    other_id = resp2.get_json()["id"]

    client.post("/urls", json={"original_url": "https://a.com", "user_id": user_id})
    client.post("/urls", json={"original_url": "https://b.com", "user_id": other_id})

    resp = client.get(f"/urls?user_id={user_id}")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_get_url(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    url_id = create_resp.get_json()["id"]

    resp = client.get(f"/urls/{url_id}")
    assert resp.status_code == 200
    assert resp.get_json()["original_url"] == "https://example.com"


def test_get_url_not_found(client):
    resp = client.get("/urls/99999")
    assert resp.status_code == 404


def test_update_url(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://old.com", "user_id": user_id})
    url_id = create_resp.get_json()["id"]

    resp = client.put(f"/urls/{url_id}", json={"title": "Updated Title"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated Title"


def test_update_url_deactivate(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    url_id = create_resp.get_json()["id"]

    resp = client.put(f"/urls/{url_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.get_json()["is_active"] is False


def test_update_url_not_found(client):
    resp = client.put("/urls/99999", json={"title": "nope"})
    assert resp.status_code == 404


def test_update_url_no_body(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    url_id = create_resp.get_json()["id"]

    resp = client.put(f"/urls/{url_id}", content_type="application/json")
    assert resp.status_code == 400


def test_redirect_short_code(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    short_code = create_resp.get_json()["short_code"]

    resp = client.get(f"/r/{short_code}")
    assert resp.status_code == 302
    assert "example.com" in resp.headers["Location"]


def test_redirect_creates_click_event(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    short_code = create_resp.get_json()["short_code"]

    client.get(f"/r/{short_code}")

    events_resp = client.get("/events")
    events = events_resp.get_json()
    click_events = [e for e in events if e["event_type"] == "click"]
    assert len(click_events) == 1


def test_redirect_not_found(client):
    resp = client.get("/r/nonexistent")
    assert resp.status_code == 404


def test_redirect_inactive_url_returns_410(client):
    user_id = _create_user(client)
    create_resp = client.post("/urls", json={"original_url": "https://example.com", "user_id": user_id})
    url_id = create_resp.get_json()["id"]
    short_code = create_resp.get_json()["short_code"]

    # Deactivate the URL
    client.put(f"/urls/{url_id}", json={"is_active": False})

    resp = client.get(f"/r/{short_code}")
    assert resp.status_code == 410
    assert "deactivated" in resp.get_json()["error"]


def test_full_url_lifecycle(client):
    """Full integration: create user -> create URL -> redirect -> check events."""
    # Create user
    user_resp = client.post("/users", json={"username": "lifecycle", "email": "lc@test.com"})
    user_id = user_resp.get_json()["id"]

    # Create URL
    url_resp = client.post("/urls", json={
        "original_url": "https://github.com",
        "user_id": user_id,
        "title": "GitHub",
    })
    assert url_resp.status_code == 201
    short_code = url_resp.get_json()["short_code"]

    # Redirect (click)
    redirect_resp = client.get(f"/r/{short_code}")
    assert redirect_resp.status_code == 302

    # Check events — should have "created" + "click"
    events = client.get("/events").get_json()
    event_types = [e["event_type"] for e in events]
    assert "created" in event_types
    assert "click" in event_types
