# Failure Modes Documentation

## Overview

This document catalogs known failure modes, how the application handles them, and what recovery mechanisms are in place.

## 1. Database Connection Failure

**Trigger:** PostgreSQL is down, credentials are wrong, or connection pool is exhausted.

**Behavior:**
- `/health` returns `503` with `"status": "degraded"` and `"database": "error: ..."`
- All database-dependent routes (users, urls, events, products) return `500`
- Errors are logged with full context

**Recovery:**
- DigitalOcean App Platform health checks poll `/health` every 10 seconds
- After consecutive failures, the container is automatically restarted
- On restart, the app reconnects to the managed Postgres database
- No data loss — Postgres is a managed service with its own availability

**How to test:**
```bash
# Stop accepting DB connections (simulated via chaos endpoint)
curl http://localhost:5001/chaos/health-fail
```

## 2. High Error Rate

**Trigger:** Application bug, bad deployment, or upstream dependency failure causing >10% of requests to return 5xx.

**Behavior:**
- Each 5xx increments `http_errors_total` Prometheus counter
- After error rate exceeds 10% for 1 minute, `HighErrorRate` alert fires
- Alertmanager sends notification to Discord within 30 seconds

**Recovery:**
- Team is notified via Discord
- If caused by bad deployment: revert via DigitalOcean dashboard or `git revert`
- CI pipeline blocks deploys if tests fail, preventing most bad deployments

**How to test:**
```bash
# Generate a flood of 500 errors
for i in $(seq 1 100); do curl -s http://localhost:5001/chaos/error; done
```

## 3. Application Crash / Process Death

**Trigger:** Unhandled exception, out-of-memory, or segfault.

**Behavior:**
- Container exits with non-zero code
- Prometheus scrape fails → `up{job="flask-app"} == 0`
- `ServiceDown` alert fires after 1 minute
- Discord notification sent

**Recovery:**
- DigitalOcean App Platform automatically restarts the container
- New container starts fresh, reconnects to database
- Typical restart time: 10-30 seconds
- No data loss (all state is in Postgres, not in-memory)

**How to test:**
```bash
# Stop the Flask app — Prometheus will detect it's down
kill $(pgrep -f "run.py")
# Wait 1-2 minutes, check Discord for ServiceDown alert
```

## 4. Bad User Input

**Trigger:** Malformed JSON, missing required fields, wrong types, invalid IDs.

**Behavior by endpoint:**

| Endpoint | Bad Input | Response |
|----------|-----------|----------|
| `POST /users` | Missing username/email | `400` with field-level errors |
| `POST /users` | Wrong types (int instead of string) | `400` with validation error |
| `POST /users` | Malformed JSON body | `400` |
| `POST /users` | No body at all | `400` |
| `GET /users/<id>` | Non-existent ID | `404` |
| `GET /users/<id>` | String instead of int | `404` |
| `POST /urls` | Missing original_url or user_id | `400` |
| `POST /urls` | Non-existent user_id | `404` |
| `GET /r/<code>` | Non-existent short code | `404` |
| `GET /r/<code>` | Deactivated URL | `410` |
| `PUT /urls/<id>` | No request body | `400` |
| `PUT /users/<id>` | Wrong field types | `400` |

**Recovery:** No recovery needed — these are client errors. The app logs warnings and returns descriptive JSON errors.

## 5. Slow Responses / High Latency

**Trigger:** Database queries taking too long, network issues, CPU saturation.

**Behavior:**
- `http_request_duration_seconds` Prometheus histogram tracks latency
- Requests eventually complete or timeout
- Gunicorn worker timeout (30s default) kills stuck workers

**Recovery:**
- Gunicorn spawns replacement workers automatically
- If caused by CPU spike: container auto-scales or restarts via health check failure

**How to test:**
```bash
# Simulate 10-second latency
curl http://localhost:5001/chaos/latency?delay=10

# Simulate CPU spike
curl http://localhost:5001/chaos/cpu?duration=30&threads=4
```

## 6. Deployment Failure

**Trigger:** New code pushed to main that breaks the app.

**Behavior:**
- GitHub Actions runs tests before deploy
- If tests fail → deploy is blocked, main stays on previous working version
- If tests pass but app still breaks in production → health check fails → container rolls back

**Recovery:**
- Automatic: CI blocks bad deploys
- Manual: `git revert <commit>` and push to trigger clean deploy
- Emergency: Redeploy previous version from DigitalOcean dashboard

## 7. Discord Webhook Failure

**Trigger:** Discord API is down, webhook URL is invalid, or rate limited.

**Behavior:**
- Alertmanager logs the failure
- Alerts are not lost — Alertmanager retries based on `repeat_interval` (4 minutes)
- The alert is still visible in the Prometheus UI at `localhost:9090/alerts`

**Recovery:**
- Alertmanager retries automatically
- Check Alertmanager UI at `localhost:9093` for queued alerts
- If webhook URL changed: update `monitoring/alertmanager.yml` and restart

## 8. Region Failure (Multi-Region)

**Trigger:** An entire region (NYC or SFO) becomes unreachable — network outage, DO regional issue, or all instances crash.

**Detection:**
- `RegionDown` Prometheus alert fires when fewer than 2 prod regions are healthy for 2+ minutes
- `ServiceDown` alert fires for the specific region

**Behavior:**
- The healthy region continues serving all traffic via the global load balancer (Cloudflare geo-routing falls back)
- Database is in NYC; if SFO goes down, no data impact. If NYC goes down, both regions lose DB access but Redis cache serves stale reads.

**Recovery:**
- Check DO status page for regional outages
- If it's a deployment issue, force rebuild: `doctl apps create-deployment <APP_ID> --force-rebuild`
- If the whole region is down, wait for DO to recover — the other region handles traffic

## 9. Cross-Region Latency

**Trigger:** SFO app instances connecting to NYC database experience ~70ms added latency per query.

**Behavior:**
- Redis cache absorbs most reads (30s TTL on lists, 60s on products)
- Cache misses incur the cross-region penalty
- Write operations always hit NYC (no way around this without multi-primary)

**Mitigation:**
- Redis is deployed per-region to keep cache local
- Hot paths (list endpoints) are cached aggressively

## 10. Monitoring Droplet Failure

**Trigger:** The monitoring Droplet (143.198.173.164) goes down.

**Impact:**
- No Prometheus scraping → no metrics → no alerts
- No Grafana dashboards
- No Loki log aggregation
- Synthetic traffic and chaos monkey stop
- App continues to work normally — monitoring is not in the request path

**Recovery:**
- SSH into the Droplet and restart Docker: `cd /root/monitoring && docker compose up -d`
- Restart systemd services: `systemctl restart synthetic-traffic`
- If the Droplet is destroyed, create a new one and run the setup script

## Recovery Summary

| Failure | Detection | Recovery | Time to Recover |
|---------|-----------|----------|-----------------|
| DB down | `/health` returns 503 | Auto-restart container | 10-30s |
| High error rate | Prometheus alert | Discord notification → team action | 1-5 min |
| App crash | Prometheus scrape fails | Auto-restart container | 10-30s |
| Bad input | N/A (client error) | JSON error response | Immediate |
| Slow response | Latency histogram | Gunicorn worker timeout + restart | 30s |
| Bad deploy | CI tests fail | Deploy blocked | Immediate |
| Webhook down | Alertmanager logs | Auto-retry | 4 min |
| Region down | RegionDown alert | Other region serves traffic | Automatic |
| Cross-region latency | Latency histogram | Redis cache absorbs reads | N/A |
| Monitoring down | No alerts firing | SSH + docker compose restart | 1-5 min |
