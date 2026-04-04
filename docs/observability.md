# Observability Guide

## Deployed Environments

| Environment | URL | Region | Instances |
|---|---|---|---|
| Prod NYC | https://pe-hackathon-muy5v.ondigitalocean.app | nyc | 3-15 (autoscale) |
| Prod SFO | https://pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app | sfo | 3-15 (autoscale) |
| Staging | https://pe-hackathon-staging-f28oj.ondigitalocean.app | nyc | 1 |

## Monitoring Stack

Hosted on a DigitalOcean Droplet at `143.198.173.164`.

| Service | URL | Login |
|---------|-----|-------|
| Grafana | http://143.198.173.164:3000 | admin / admin |
| Prometheus | http://143.198.173.164:9090 | — |
| Alertmanager | http://143.198.173.164:9093 | — |
| Loki | http://143.198.173.164:3100 | — |

## Endpoints (available on all environments)

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check with region, instance_id, DB status |
| `/metrics` | CPU and memory usage (JSON) |
| `/logs` | View structured logs, `?level=ERROR`, `?limit=N` |
| `/prom-metrics` | Prometheus text format metrics |
| `/alerts` | Alert management (list, create, ack, resolve) |

## Grafana Dashboards

### Overview Dashboard
Tracks the 4 golden signals with region/environment dropdowns:
- **Traffic** — request rate per second by region
- **Errors** — error rate percentage by region
- **Latency** — p50, p95, p99 response times
- **Saturation** — CPU and memory usage

### Log Explorer (Loki)
Go to Explore → select Loki datasource. Example queries:
```
{job="flask-app"}                              # all logs
{job="flask-app", region="nyc"}                # NYC only
{job="flask-app", environment="staging"}       # staging only
{job="flask-app"} |= "ERROR"                  # errors only
{job="flask-app", instance_id="abc12345"}      # specific instance
```

## Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| ServiceDown | App unreachable for 1 minute | Critical |
| HighErrorRate | >10% 5xx over 2 minutes | Warning |
| HighLatencyP95 | p95 > 2s for 2 minutes | Warning |
| RegionDown | Fewer than 2 prod regions healthy | Critical |

Alerts fire to Discord with deep links to Grafana dashboard, Loki logs, and the runbook.

### Alert Management
```bash
# List active alerts
curl https://<app-url>/alerts?status=firing

# Acknowledge an alert
curl -X PUT https://<app-url>/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged", "acknowledged_by": "your-name", "notes": "Investigating"}'

# Resolve
curl -X PUT https://<app-url>/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "notes": "Root cause: DNS timeout, fixed by restarting"}'
```

## Chaos Endpoints

| Endpoint | Description |
|----------|-------------|
| `/chaos/error` | Single 500 error |
| `/chaos/error-flood?count=50` | Burst of errors |
| `/chaos/cpu?duration=10&threads=4` | CPU spike |
| `/chaos/latency?delay=5` | Slow response |
| `/chaos/health-fail` | 503 response |
| `/chaos/critical` | Direct Discord alert |

## Automated Systems

### Synthetic Traffic (24/7)
Runs on the monitoring Droplet as a systemd service. Generates realistic traffic (create users, create URLs, redirect clicks, list data) against all three environments every 10 seconds.

```bash
# Check status
ssh root@143.198.173.164 "systemctl status synthetic-traffic"
ssh root@143.198.173.164 "journalctl -u synthetic-traffic -f"
```

### Chaos Monkey (every 30 min)
Runs on a systemd timer. Picks a random chaos endpoint, hits a random prod region, verifies alerts fire.

```bash
# Check status
ssh root@143.198.173.164 "systemctl list-timers chaos-monkey.timer"
ssh root@143.198.173.164 "journalctl -u chaos-monkey --no-pager -n 20"
```

## Architecture

```
                   Cloudflare Global LB (geo-routing)
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
        NYC Region                      SFO Region
   ┌─────────────────┐            ┌─────────────────┐
   │ Prod App        │            │ Prod App        │
   │ 3-15 instances  │            │ 3-15 instances  │
   │ + Redis cache   │            │ + Redis cache   │
   └────────┬────────┘            └────────┬────────┘
            │                              │
            └──────────┬───────────────────┘
                       ▼
              Managed Postgres (NYC)

   NYC Region (also)
   ┌─────────────────┐
   │ Staging App     │
   │ 1 instance      │
   │ (staging branch)│
   └─────────────────┘

   Monitoring Droplet (143.198.173.164)
   ┌──────────────────────────────┐
   │ Prometheus  ← scrapes all 3 │
   │ Grafana     ← dashboards    │
   │ Loki        ← centralized   │
   │ Alertmanager → Discord      │
   │ Synthetic Traffic (24/7)    │
   │ Chaos Monkey (every 30m)    │
   └──────────────────────────────┘
```

## Structured Logging

Every log entry includes:
- `timestamp`, `level`, `message` — standard fields
- `instance_id` — unique per process (8-char UUID)
- `region` — nyc, sfo, or local
- `environment` — prod, staging, or dev
- `method`, `path`, `status` — on request logs

Logs ship to Loki via HTTP push for centralized search.

## Local Development

```bash
uv run run.py  # http://localhost:5001
```

For local monitoring:
```bash
cd monitoring && docker compose up -d
```
