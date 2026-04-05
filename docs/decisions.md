# Technical Decision Log

## 1. App Platform over raw Droplets

**Decision:** Host the Flask app on DigitalOcean App Platform instead of self-managed Droplets.

**Why:** App Platform provides auto-restart on crash, zero-downtime deploys, built-in health checks, and HTTPS termination. Raw droplets required manual Docker management, had no automatic recovery, and a single disk failure would lose all data. For a hackathon focused on reliability, using managed infrastructure is the right trade-off — we focus on application-level resilience instead of OS-level ops.

**Trade-off:** Less control over the runtime environment, slightly higher cost per instance.

## 2. Managed Postgres and Redis

**Decision:** Use DigitalOcean Managed Databases for both Postgres and Redis instead of self-hosted containers.

**Why:** Managed databases provide automated daily backups, point-in-time recovery, failover, and connection pooling. Self-hosted databases on a droplet have no backup unless manually configured, and a droplet failure means data loss. For a URL shortener where data persistence matters, managed databases are non-negotiable.

**Trade-off:** Higher cost ($15/mo each vs ~$0 for containerized), but eliminates entire classes of failure.

## 3. Separate Monitoring Droplet

**Decision:** Keep monitoring (Prometheus, Grafana, Loki) on a separate Droplet rather than co-locating with the app or using a managed monitoring service.

**Why:** If monitoring runs on the same infrastructure as the app, chaos engineering tests (CPU spikes, process kills) take down the dashboards too — you can't observe the failure you just caused. A separate droplet ensures the observer survives when the observed fails. We chose a Droplet over Grafana Cloud because provisioning dashboards-as-code from git is a better demo of infrastructure-as-code practices.

**Trade-off:** One more piece of infrastructure to manage, but it's the observer — if it goes down briefly, we lose visibility, not production traffic.

## 4. Grafana Alerting over Prometheus Alertmanager

**Decision:** Use Grafana's built-in alerting instead of Prometheus Alertmanager for alert evaluation and routing.

**Why:** Grafana alerting supports provisioning via YAML files (infrastructure-as-code), provides dashboard links directly in alert notifications, and keeps alert configuration alongside the dashboards it monitors. Prometheus Alertmanager is a separate system with its own config format, adding unnecessary complexity.

**Trade-off:** Grafana alerting is slightly less mature than Alertmanager for complex routing, but our routing is simple (everything goes to Discord).

## 5. Redis for Caching with Graceful Degradation

**Decision:** Use Redis for caching hot paths (`/products`, `/users`, `/urls`) with the app falling back to direct DB queries if Redis is unavailable.

**Why:** Under load testing, database queries were the primary bottleneck. Adding Redis with 30-60s TTLs reduced p95 latency and increased throughput from 273 req/s to 330 req/s at 500 concurrent users. Graceful degradation means a Redis outage slows the app but doesn't break it.

**Trade-off:** Added complexity in cache invalidation. We use short TTLs (30-60s) rather than explicit invalidation to keep it simple.

## 6. Single Region (NYC)

**Decision:** Consolidate from multi-region (NYC + SFO) to a single region.

**Why:** Multi-region added complexity (separate Redis clusters per region, cross-region DB latency, dual deploy pipelines) without meaningful benefit for this project. A single region with managed database backups provides sufficient reliability. The hackathon evaluation doesn't require geographic redundancy.

**Trade-off:** No geographic failover, higher latency for users far from NYC. Acceptable for a demo.

## 7. Structured JSON Logging with Loki

**Decision:** Use python-json-logger for structured log output, shipped to Grafana Loki via a custom handler.

**Why:** Structured logs enable querying by field (level, component, status code) rather than regex-matching plaintext. Loki provides centralized log aggregation across instances. The custom LokiHandler uses a background thread with a queue to avoid blocking request handling.

**Trade-off:** Slightly more complex logging setup, but the ability to query `{job="flask-app"} | json | level="ERROR"` in Grafana is worth it.

## 8. k6 over Locust for Load Testing

**Decision:** Use k6 for load testing instead of Locust.

**Why:** k6 scripts are plain JavaScript, run from a single binary with no Python dependencies, and have built-in support for thresholds (p95 < 5s, error rate < 10%) that fail the test automatically. The `handleSummary` function lets us POST results back to the app for tracking.

**Trade-off:** Less flexible than Locust for complex user flows, but simpler for threshold-based pass/fail testing.
