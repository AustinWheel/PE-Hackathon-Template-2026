"""Integration tests for /users endpoints."""
import io


def test_create_user(client):
    resp = client.post("/users", json={"username": "alice", "email": "alice@test.com"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@test.com"
    assert "id" in data
    assert "created_at" in data


def test_create_user_missing_username(client):
    resp = client.post("/users", json={"email": "alice@test.com"})
    assert resp.status_code == 400
    assert "errors" in resp.get_json()
    assert "username" in resp.get_json()["errors"]


def test_create_user_missing_email(client):
    resp = client.post("/users", json={"username": "alice"})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["errors"]


def test_create_user_missing_both(client):
    resp = client.post("/users", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    # May return "errors" dict or "error" string depending on validation path
    assert "errors" in data or "error" in data


def test_create_user_no_body(client):
    resp = client.post("/users", content_type="application/json")
    assert resp.status_code == 400


def test_create_user_invalid_username_type(client):
    resp = client.post("/users", json={"username": 123, "email": "a@b.com"})
    assert resp.status_code == 400
    assert "username" in resp.get_json()["errors"]


def test_create_user_invalid_email_type(client):
    resp = client.post("/users", json={"username": "alice", "email": 123})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["errors"]


def test_get_user(client):
    create_resp = client.post("/users", json={"username": "bob", "email": "bob@test.com"})
    user_id = create_resp.get_json()["id"]

    resp = client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "bob"


def test_get_user_not_found(client):
    resp = client.get("/users/99999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_list_users(client):
    client.post("/users", json={"username": "u1", "email": "u1@test.com"})
    client.post("/users", json={"username": "u2", "email": "u2@test.com"})

    resp = client.get("/users")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_users_pagination(client):
    for i in range(5):
        client.post("/users", json={"username": f"u{i}", "email": f"u{i}@test.com"})

    resp = client.get("/users?page=1&per_page=2")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_update_user(client):
    create_resp = client.post("/users", json={"username": "old", "email": "old@test.com"})
    user_id = create_resp.get_json()["id"]

    resp = client.put(f"/users/{user_id}", json={"username": "new"})
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "new"
    assert resp.get_json()["email"] == "old@test.com"  # unchanged


def test_update_user_email(client):
    create_resp = client.post("/users", json={"username": "alice", "email": "old@test.com"})
    user_id = create_resp.get_json()["id"]

    resp = client.put(f"/users/{user_id}", json={"email": "new@test.com"})
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "new@test.com"


def test_update_user_not_found(client):
    resp = client.put("/users/99999", json={"username": "nope"})
    assert resp.status_code == 404


def test_update_user_no_body(client):
    create_resp = client.post("/users", json={"username": "alice", "email": "a@b.com"})
    user_id = create_resp.get_json()["id"]

    resp = client.put(f"/users/{user_id}", content_type="application/json")
    assert resp.status_code == 400


def test_update_user_invalid_username_type(client):
    create_resp = client.post("/users", json={"username": "alice", "email": "a@b.com"})
    user_id = create_resp.get_json()["id"]

    resp = client.put(f"/users/{user_id}", json={"username": 123})
    assert resp.status_code == 400


def test_create_then_get_roundtrip(client):
    """Full integration: create a user, retrieve it, verify all fields match."""
    create_resp = client.post("/users", json={"username": "roundtrip", "email": "rt@test.com"})
    assert create_resp.status_code == 201
    created = create_resp.get_json()

    get_resp = client.get(f"/users/{created['id']}")
    assert get_resp.status_code == 200
    fetched = get_resp.get_json()

    assert fetched["id"] == created["id"]
    assert fetched["username"] == "roundtrip"
    assert fetched["email"] == "rt@test.com"


def test_bulk_upload_users(client):
    csv_data = "username,email\nbulk1,bulk1@test.com\nbulk2,bulk2@test.com"
    data = {"file": (io.BytesIO(csv_data.encode()), "users.csv")}

    resp = client.post("/users/bulk", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    assert resp.get_json()["count"] == 2

    # Verify they're actually in the DB
    list_resp = client.get("/users")
    assert len(list_resp.get_json()) == 2


def test_bulk_upload_no_file(client):
    resp = client.post("/users/bulk", content_type="multipart/form-data")
    assert resp.status_code == 400
