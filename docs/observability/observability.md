# Observability Guide

## Deployed Environments

| Environment | URL | Instances |
|---|---|---|
| Production | https://pe-hackathon-hni9m.ondigitalocean.app | 2 (App Platform) |
| Staging | https://pe-hackathon-staging-stj5i.ondigitalocean.app | 1 (App Platform) |

## Monitoring Stack

Hosted on a DigitalOcean Droplet at `143.198.173.164`.

| Service | URL | Login |
|---|---|---|
| Grafana | http://143.198.173.164:3000 | admin / admin |
| Prometheus | http://143.198.173.164:9090 | — |
| Alertmanager | http://143.198.173.164:9093 | — |
| Loki | http://143.198.173.164:3100 | — |

## Endpoints

| Endpoint | Description |
|---|---|
| `/health` | Health check — instance_id, DB status, uptime |
| `/metrics` | CPU and memory usage (JSON) |
| `/logs` | View structured logs, `?level=ERROR`, `?limit=N` |
| `/prom-metrics` | Prometheus text format metrics |
| `/alerts` | Alert management (list, create, ack, resolve) |
| `/loadtest/results` | Load test result history |

## Grafana Dashboards

### Production Overview (`/d/overview/`)
Tracks the 4 golden signals:
- **Traffic** — request rate per second (prod vs staging)
- **Errors** — error rate percentage, 5xx by endpoint, 4xx/5xx by status code
- **Latency** — p50, p95, p99 response times, per-endpoint breakdown
- **Saturation** — CPU, memory, in-flight requests, file descriptors

### Logs Explorer (`/d/logs/`)
- Log volume by level (INFO/WARNING/ERROR/CRITICAL)
- Error and warning log stream
- Application logs (full stream)
- Chaos monkey logs (filtered)
- Alert system logs (filtered)

### Loki Queries (Explore tab)
```
{job="flask-app"}                              # all logs
{job="flask-app", environment="prod"}          # prod only
{job="flask-app"} |= "ERROR"                  # errors only
{job="flask-app"} | json | component="chaos"   # chaos events
{job="flask-app"} | json | status >= 500       # 5xx responses
```

## Alerts

Managed via Grafana Alerting (provisioned as code in `monitoring/grafana/provisioning/alerting/`).

| Alert | Condition | Severity | For |
|---|---|---|---|
| Service Down — Prod | `app_up < 1` | Critical | 1m |
| Service Down — Staging | `app_up < 1` | Warning | 1m |
| High Error Rate | Error rate > 10% | Warning | 30s |
| Critical Error Rate | Error rate > 25% | Critical | 30s |
| High P95 Latency | p95 > 2s | Warning | 2m |
| Extreme P99 Latency | p99 > 5s | Critical | 2m |
| High CPU | CPU > 80% | Warning | 2m |
| High Memory | Memory > 85% | Warning | 2m |
| High Saturation | In-flight requests > 50 | Warning | 1m |

All alerts fire to Discord with links to the relevant Grafana dashboard panel.

### Alert Management
```bash
# List active alerts
curl https://pe-hackathon-hni9m.ondigitalocean.app/alerts?status=firing

# Acknowledge an alert
curl -X PUT https://pe-hackathon-hni9m.ondigitalocean.app/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged", "acknowledged_by": "your-name"}'

# Resolve
curl -X PUT https://pe-hackathon-hni9m.ondigitalocean.app/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "notes": "Root cause identified and fixed"}'
```

## Chaos Endpoints

| Endpoint | Description |
|---|---|
| `/chaos/error` | Single 500 error |
| `/chaos/error-flood?count=50` | Burst of errors (creates alert in DB) |
| `/chaos/cpu?duration=10&threads=4` | CPU spike |
| `/chaos/latency?delay=5` | Slow response |
| `/chaos/health-fail` | 503 health failure (creates alert in DB) |
| `/chaos/critical` | Critical alert to Discord (creates alert in DB) |

## Automated Systems

### Synthetic Traffic (24/7)
Runs on the monitoring Droplet. Generates realistic traffic (create users, URLs, redirect clicks) against production every 3 seconds.

```bash
ssh root@143.198.173.164 "systemctl status synthetic-traffic"
ssh root@143.198.173.164 "journalctl -u synthetic-traffic -f"
```

### Chaos Monkey (every 5 min)
Picks a random chaos action, hits production, verifies alerts fire.

```bash
ssh root@143.198.173.164 "systemctl list-timers chaos-monkey.timer"
ssh root@143.198.173.164 "journalctl -u chaos-monkey --no-pager -n 20"
```

## Structured Logging

Every log entry is JSON with these fields:
- `timestamp`, `level`, `message` — standard fields
- `instance_id` — unique per process (8-char UUID)
- `environment` — prod, staging, or dev
- `method`, `path`, `status` — on request/response logs
- `component` — functional area (chaos, alerts, health, etc.)

Logs ship to Loki via HTTP push (background thread, non-blocking) for centralized search.

## Prometheus Metrics Exposed

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | Total requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request latency by method, endpoint |
| `http_errors_total` | Counter | Total 5xx errors by method, endpoint |
| `http_requests_in_flight` | Gauge | Currently processing requests |
| `app_up` | Gauge | 1 if healthy, 0 if not |
| `system_cpu_percent` | Gauge | CPU usage percentage |
| `system_memory_percent` | Gauge | Memory usage percentage |
| `system_memory_used_bytes` | Gauge | Memory in use (bytes) |
| `process_resident_memory_bytes` | Gauge | RSS memory |
| `process_open_fds` | Gauge | Open file descriptors |
