# Error Handling Documentation

## Overview

All endpoints return JSON responses with appropriate HTTP status codes. Errors include a descriptive `error` field. Validation failures return an `errors` object keyed by field name.

## HTTP Status Codes Used

| Code | Meaning | When it's returned |
|------|---------|-------------------|
| 200 | OK | Successful GET, PUT |
| 201 | Created | Successful POST (user, URL) |
| 302 | Redirect | Successful short URL redirect (`/r/<code>`) |
| 400 | Bad Request | Missing required fields, invalid types, no request body |
| 404 | Not Found | Resource doesn't exist (user, URL, short code) |
| 410 | Gone | Deactivated short URL accessed via `/r/<code>` |
| 500 | Internal Server Error | Unhandled exception, database failure |
| 503 | Service Unavailable | Health check fails (DB unreachable) |

## How 404s Are Handled

Every endpoint that looks up a resource by ID or code catches `DoesNotExist` exceptions and returns a JSON error:

**User not found:**
```json
GET /users/99999 → 404
{"error": "User not found"}
```

**URL not found:**
```json
GET /urls/99999 → 404
{"error": "URL not found"}
```

**Short code not found:**
```json
GET /r/nonexistent → 404
{"error": "Short URL not found"}
```

**Creating URL for nonexistent user:**
```json
POST /urls {"user_id": 99999, "original_url": "..."} → 404
{"error": "User not found"}
```

## How 400s Are Handled

Input validation returns field-level errors so the client knows exactly what to fix:

**Missing required fields:**
```json
POST /users {"username": "alice"} → 400
{"errors": {"email": "email is required"}}
```

**Wrong field types:**
```json
POST /users {"username": 123, "email": "a@b.com"} → 400
{"errors": {"username": "username must be a string"}}
```

**No request body:**
```json
POST /users (empty body) → 400
{"error": "Request body is required"}
```

**Missing URL fields:**
```json
POST /urls {} → 400
{"error": "original_url and user_id are required"}
```

## How 410s Are Handled

Deactivated URLs return 410 Gone instead of redirecting:

```json
GET /r/abc123 (where abc123 is deactivated) → 410
{"error": "This URL has been deactivated"}
```

## How 500s Are Handled

Unhandled exceptions in route handlers are caught by try/except blocks and return a generic error. The actual exception is logged but not exposed to the client:

```json
GET /products (if DB query fails) → 500
{"error": "Internal server error"}
```

All 500 errors are:
1. Logged with full stack trace via structured JSON logging
2. Counted by the `http_errors_total` Prometheus metric
3. Visible in the `/logs?level=ERROR` endpoint
4. Trigger the **HighErrorRate** Prometheus alert if rate exceeds 10%

## How 503s Are Handled

The `/health` endpoint checks database connectivity. If the DB is unreachable:

```json
GET /health → 503
{
  "status": "degraded",
  "version": "0.1.0",
  "uptime_seconds": 3600.5,
  "database": "error: connection refused"
}
```

DigitalOcean App Platform uses this endpoint for health checks and will restart the container if it returns 503 repeatedly.

## Logging

All errors are logged in structured JSON format to both stdout and `app.log`:

```json
{
  "timestamp": "2026-04-04T12:00:00",
  "level": "ERROR",
  "name": "app.routes.users",
  "message": "User not found",
  "component": "users",
  "user_id": 99999
}
```

Every log entry includes:
- `timestamp` — when the error occurred
- `level` — ERROR, WARNING, INFO, CRITICAL
- `component` — which route module generated it
- Contextual fields (user_id, short_code, etc.)

## Alert Flow for Errors

```
Error occurs → Logged to stdout + app.log
            → http_errors_total Prometheus counter incremented
            → Prometheus evaluates alert rules every 15s
            → If error rate > 10% for 1+ minute → Alertmanager fires
            → Discord webhook receives notification
```
