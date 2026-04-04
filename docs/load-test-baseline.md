# Load Test Baseline Results

## Test Configuration

- **Tool:** k6 v1.7.1
- **Concurrent Users:** 50
- **Duration:** 10s ramp-up → 30s hold → 10s ramp-down
- **Target:** Flask app on localhost:5001 (single instance, debug mode)
- **Endpoints tested:** /health, /products, /users, /urls, /metrics
- **Database:** PostgreSQL (local, seeded with 400 users, 2000 urls, 3422 events)

## Results Summary

| Metric | Value |
|--------|-------|
| **Total Requests** | 5,130 |
| **Throughput** | 101 req/s |
| **Error Rate** | 0.00% |
| **p50 Latency** | 160ms |
| **p90 Latency** | 418ms |
| **p95 Latency** | 460ms |
| **Max Latency** | 558ms |

## Per-Endpoint Latency (p95)

| Endpoint | p95 Latency | Avg Latency |
|----------|-------------|-------------|
| /health | 501ms | 313ms |
| /products | 243ms | 118ms |
| /users | 250ms | 117ms |
| /urls | 497ms | 291ms |
| /metrics | N/A (system) | N/A |

## Observations

- **Zero errors** at 50 concurrent users — the app handles this load cleanly
- **/urls** and **/health** are the slowest endpoints (~500ms p95), likely due to:
  - /urls returns all 2000 URLs without pagination by default (large payload)
  - /health performs a `SELECT 1` DB check on every call
- **/products** and **/users** are faster (~250ms p95) since /users is paginated and /products has fewer rows
- **Throughput of 101 req/s** with a single Flask dev server is a solid baseline
- Flask's built-in dev server is single-threaded — production deployment with Gunicorn/multiple workers would improve this significantly

## Bottlenecks Identified

1. **Single-threaded Flask dev server** — limits concurrency to one request at a time
2. **/urls endpoint** — returns all rows without pagination, causing large response payloads
3. **No caching** — every request hits the database, even for data that rarely changes
4. **Database connection per request** — connection setup/teardown overhead on each request

## Next Steps (Silver/Gold)

- Add Gunicorn with multiple workers
- Dockerize the app and run multiple instances
- Add Nginx load balancer
- Implement Redis caching for frequently-accessed endpoints
- Add pagination to /urls endpoint
