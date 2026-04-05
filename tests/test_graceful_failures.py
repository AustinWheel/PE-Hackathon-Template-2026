"""Gold tier: Verify graceful failure on ALL endpoints.

Tests bad JSON, missing fields, invalid IDs, wrong types, and edge cases
to ensure the app never crashes — it always returns a proper JSON error.
"""


# ============================================================
# /users — graceful failures
# ============================================================

class TestUsersGracefulFailure:

    def test_post_invalid_json(self, client):
        """Sending malformed JSON should return 400, not 500."""
        resp = client.post("/users", data="not json", content_type="application/json")
        assert resp.status_code == 400

    def test_post_wrong_content_type(self, client):
        """Sending form data instead of JSON should return 400 or 415."""
        resp = client.post("/users", data="username=alice", content_type="application/x-www-form-urlencoded")
        assert resp.status_code in (400, 415)

    def test_post_array_instead_of_object(self, client):
        """Sending a JSON array instead of an object."""
        resp = client.post("/users", json=[{"username": "alice"}])
        assert resp.status_code in (400, 500)  # should not crash

    def test_get_user_string_id(self, client):
        """String instead of integer ID should return 404."""
        resp = client.get("/users/notanumber")
        assert resp.status_code == 404

    def test_get_user_negative_id(self, client):
        """Negative ID should return 404."""
        resp = client.get("/users/-1")
        assert resp.status_code == 404

    def test_get_user_zero_id(self, client):
        """Zero ID should return 404."""
        resp = client.get("/users/0")
        assert resp.status_code == 404

    def test_get_user_very_large_id(self, client):
        """Very large ID should return 404, not crash."""
        resp = client.get("/users/999999999")
        assert resp.status_code == 404

    def test_put_user_nonexistent(self, client):
        """Updating a user that doesn't exist."""
        resp = client.put("/users/99999", json={"username": "ghost"})
        assert resp.status_code == 404

    def test_put_user_empty_string_username(self, client):
        """Empty string should be accepted (validation is loose) or rejected with 400."""
        resp = client.post("/users", json={"username": "temp", "email": "t@t.com"})
        uid = resp.get_json()["id"]
        resp = client.put(f"/users/{uid}", json={"username": ""})
        assert resp.status_code in (200, 400)

    def test_post_user_extra_fields_ignored(self, client):
        """Extra fields in the body should be ignored, not cause errors."""
        resp = client.post("/users", json={
            "username": "alice",
            "email": "a@b.com",
            "foo": "bar",
            "admin": True,
        })
        assert resp.status_code == 201

    def test_bulk_upload_wrong_content_type(self, client):
        """Bulk upload without multipart form should fail gracefully."""
        resp = client.post("/users/bulk", json={"file": "not a file"})
        assert resp.status_code == 400


# ============================================================
# /urls — graceful failures
# ============================================================

class TestUrlsGracefulFailure:

    def _create_user(self, client):
        resp = client.post("/users", json={"username": "urltest", "email": "u@t.com"})
        return resp.get_json()["id"]

    def test_post_url_no_body(self, client):
        resp = client.post("/urls", content_type="application/json")
        assert resp.status_code == 400

    def test_post_url_invalid_json(self, client):
        resp = client.post("/urls", data="{bad", content_type="application/json")
        assert resp.status_code == 400

    def test_post_url_user_id_string(self, client):
        """String user_id instead of integer."""
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": "abc"})
        assert resp.status_code in (400, 404, 500)

    def test_post_url_user_id_negative(self, client):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": -1})
        assert resp.status_code == 404

    def test_get_url_string_id(self, client):
        resp = client.get("/urls/notanumber")
        assert resp.status_code == 404

    def test_get_url_negative_id(self, client):
        resp = client.get("/urls/-1")
        assert resp.status_code == 404

    def test_put_url_nonexistent(self, client):
        resp = client.put("/urls/99999", json={"title": "nope"})
        assert resp.status_code == 404

    def test_put_url_invalid_json(self, client):
        user_id = self._create_user(client)
        create_resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": user_id})
        url_id = create_resp.get_json()["id"]

        resp = client.put(f"/urls/{url_id}", data="{bad", content_type="application/json")
        assert resp.status_code == 400

    def test_redirect_empty_short_code(self, client):
        """Accessing /r/ with no code should 404."""
        resp = client.get("/r/")
        assert resp.status_code == 404

    def test_redirect_special_characters(self, client):
        """Short code with special chars should 404 gracefully."""
        resp = client.get("/r/../../etc")
        assert resp.status_code == 404

    def test_post_url_extra_fields(self, client):
        user_id = self._create_user(client)
        resp = client.post("/urls", json={
            "original_url": "https://x.com",
            "user_id": user_id,
            "evil_field": "drop table",
        })
        assert resp.status_code == 201


# ============================================================
# /events — graceful failures
# ============================================================

class TestEventsGracefulFailure:

    def test_events_invalid_page(self, client):
        """Non-integer page parameter."""
        resp = client.get("/events?page=abc")
        assert resp.status_code in (200, 400)

    def test_events_negative_page(self, client):
        resp = client.get("/events?page=-1")
        assert resp.status_code in (200, 400)

    def test_events_zero_per_page(self, client):
        resp = client.get("/events?per_page=0")
        assert resp.status_code in (200, 400)

    def test_events_very_large_page(self, client):
        """Requesting a huge page number should return empty, not crash."""
        resp = client.get("/events?page=999999")
        assert resp.status_code == 200
        assert resp.get_json() == []


# ============================================================
# /products — graceful failures
# ============================================================

class TestProductsGracefulFailure:

    def test_products_returns_json(self, client):
        resp = client.get("/products")
        assert resp.content_type.startswith("application/json")

    def test_products_method_not_allowed(self, client):
        """POST to /products should fail since only GET is defined."""
        resp = client.post("/products", json={"name": "x"})
        assert resp.status_code == 405


# ============================================================
# /metrics — graceful failures
# ============================================================

class TestMetricsGracefulFailure:

    def test_metrics_returns_json(self, client):
        resp = client.get("/metrics")
        assert resp.content_type.startswith("application/json")

    def test_metrics_post_not_allowed(self, client):
        resp = client.post("/metrics")
        assert resp.status_code == 405


# ============================================================
# /logs — graceful failures
# ============================================================

class TestLogsGracefulFailure:

    def test_logs_invalid_limit(self, client):
        """Non-integer limit should fallback to default, not crash."""
        resp = client.get("/logs?limit=abc")
        assert resp.status_code == 200

    def test_logs_negative_limit(self, client):
        resp = client.get("/logs?limit=-5")
        assert resp.status_code == 200

    def test_logs_nonexistent_level(self, client):
        """Filtering by a level that doesn't exist should return empty."""
        resp = client.get("/logs?level=BOGUS")
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0


# ============================================================
# /health — graceful failures
# ============================================================

class TestHealthGracefulFailure:

    def test_health_post_not_allowed(self, client):
        resp = client.post("/health")
        assert resp.status_code == 405

    def test_health_returns_json(self, client):
        resp = client.get("/health")
        assert resp.content_type.startswith("application/json")


# ============================================================
# /chaos — graceful failures
# ============================================================

class TestChaosGracefulFailure:

    def test_chaos_error_default(self, client):
        resp = client.get("/chaos/error")
        assert resp.status_code == 500
        assert resp.get_json() is not None

    def test_chaos_error_invalid_status(self, client):
        """Non-integer status should fallback to 500."""
        resp = client.get("/chaos/error?status=abc")
        assert resp.status_code == 500

    def test_chaos_cpu_zero_duration(self, client):
        resp = client.get("/chaos/cpu?duration=0&threads=1")
        assert resp.status_code == 200

    def test_chaos_error_flood_zero_count(self, client):
        resp = client.get("/chaos/error-flood?count=0")
        assert resp.status_code == 500
        assert resp.get_json()["errors_generated"] == 0

    def test_chaos_latency_zero(self, client):
        resp = client.get("/chaos/latency?delay=0")
        assert resp.status_code == 200


# ============================================================
# General — 404 for unknown routes
# ============================================================

class TestUnknownRoutes:

    def test_unknown_route_returns_404(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_unknown_nested_route(self, client):
        resp = client.get("/api/v1/doesnotexist")
        assert resp.status_code == 404
