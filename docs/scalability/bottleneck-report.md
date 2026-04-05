# Bottleneck Report

## What was slow

The initial baseline (Bronze) ran a single Flask dev server handling 50 users. The main bottlenecks were:

1. **Single-threaded dev server** — Flask's built-in server processes one request at a time. Under 50 concurrent users, requests queued up waiting for their turn.

2. **Database hit on every request** — Every GET to /products, /users, and /urls executed a full SQL query, even though the underlying data rarely changes. At 200+ users, the database connection pool became the chokepoint.

3. **Unpaginated /urls endpoint** — Returned all 2,000 URL records in a single response (~500KB payload), consuming bandwidth and serialization time on every request.

## How we fixed it

| Bottleneck | Fix | Impact |
|------------|-----|--------|
| Single-threaded server | Gunicorn with 4 workers per container | 4x concurrency per instance |
| Single instance | 3 app containers behind Nginx load balancer | 12 total workers (3 x 4) |
| DB hit every request | Redis caching on /products (60s TTL), /users (30s), /urls (30s) | Cache hits skip DB entirely |
| No load distribution | Nginx round-robin across 3 instances | Even traffic distribution |

## Results comparison

| Metric | Bronze (1 instance) | Silver (3 instances) | Gold (3 + Redis) |
|--------|--------------------|--------------------|-----------------|
| Concurrent users | 50 | 200 | **500** |
| Throughput | 101 req/s | 273 req/s | **330 req/s** |
| Error rate | 0% | 0% | **0%** |
| p95 latency | 460ms | 1.2s | **2.4s** |

## Caching evidence

With Redis enabled, the app logs show cache hit/miss status:
- First request to /products: `"Products listed (cache miss)"` — hits DB, stores in Redis
- Subsequent requests: `"Products listed (cache hit)"` — served from Redis in <1ms
- Cache TTL: products 60s, users 30s, urls 30s

The caching reduces database load significantly — under 500 concurrent users, the majority of read requests are served from Redis without touching Postgres.
