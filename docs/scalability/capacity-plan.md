# Capacity Plan

## Current Configuration

| Component | Spec | Capacity |
|---|---|---|
| App instances | 2x apps-d-1vcpu-2gb | 4 gunicorn workers each, 8 total |
| PostgreSQL | db-s-1vcpu-1gb | ~100 concurrent connections |
| Redis/Valkey | db-s-1vcpu-1gb | ~10,000 ops/sec |
| Monitoring | s-2vcpu-4gb droplet | Prometheus + Grafana + Loki |

## Measured Performance

From k6 load testing against production:

| Tier | Concurrent Users | Requests/sec | P95 Latency | Error Rate |
|---|---|---|---|---|
| Bronze | 50 | ~100 req/s | < 500ms | < 1% |
| Silver | 200 | ~270 req/s | < 3s | < 5% |
| Gold | 500 | ~330 req/s | < 5s | < 5% |

## Bottleneck Analysis

1. **Database queries** — the primary bottleneck. Mitigated by Redis caching (30-60s TTL on read-heavy endpoints)
2. **Gunicorn workers** — 4 workers per instance can handle ~40 concurrent requests before queuing. Monitored via `http_requests_in_flight` metric
3. **Single-threaded GIL** — Python's GIL limits CPU-bound work per worker. CPU spikes from chaos testing confirm this

## Scaling Strategy

### Vertical (quick wins)
- Upgrade to `apps-d-2vcpu-4gb` instances — doubles worker count to 8 per instance
- Upgrade Postgres to `db-s-2vcpu-4gb` — more connections, larger shared_buffers

### Horizontal (for sustained growth)
- Increase `instance_count` in `.do/app.yaml` — App Platform handles load balancing
- Current: 2 instances. Can scale to 10+ without config changes
- Each additional instance adds ~165 req/s capacity

### Projected Limits

| Instance Count | Est. Throughput | Est. Max Users |
|---|---|---|
| 2 (current) | ~330 req/s | ~500 |
| 4 | ~660 req/s | ~1,000 |
| 8 | ~1,300 req/s | ~2,000 |

## Cost

| Component | Monthly Cost |
|---|---|
| App Platform (2x apps-d-1vcpu-2gb) | $24 |
| Managed Postgres (db-s-1vcpu-1gb) | $15 |
| Managed Redis (db-s-1vcpu-1gb) | $15 |
| Monitoring Droplet (s-2vcpu-4gb) | $24 |
| Staging App Platform (basic-xxs) | $5 |
| **Total** | **~$83/mo** |

Scaling to 4 instances adds ~$12/mo. Database upgrades add ~$30/mo each.

## Alerts for Capacity

These Grafana alerts fire before capacity is exhausted:
- **High CPU > 80%** — indicates need for more instances or larger instances
- **High Memory > 85%** — indicates memory pressure, potential OOM
- **In-flight requests > 50** — indicates request queuing, add instances
- **P95 latency > 2s** — indicates saturation, scale horizontally
