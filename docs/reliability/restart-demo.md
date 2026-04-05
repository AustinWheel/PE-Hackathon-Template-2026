# Service Restart Demo Script

## What we're demonstrating
When the app fails health checks, App Platform automatically kills and restarts the instance. We trigger this with the `/chaos/health-fail` endpoint, which makes `/health` return 503 for 60 seconds. App Platform polls `/health` every 10s — after 3 consecutive failures (30s), it restarts the instance.

## What we'll show

1. **Terminal** — health check loop
2. **Browser** — DigitalOcean App Platform dashboard → pe-hackathon → Runtime Logs
3. **Browser** — Grafana dashboard at http://143.198.173.164:3000/d/overview/

## Steps

### 1. Healthy state

```bash
while true; do
  echo "$(date +%H:%M:%S) $(curl -s -o /dev/null -w '%{http_code}' https://pe-hackathon-hni9m.ondigitalocean.app/health)"
  sleep 2
done
```

### 2. Trigger the failure

```bash
curl -s https://pe-hackathon-hni9m.ondigitalocean.app/chaos/health-fail?duration=60 | python3 -m json.tool
```

### 3. Show health checks failing

Health checks start to show failures

### 4. Show App Platform restarting (~15s)

Switch to the DO dashboard Runtime Logs. You'll see:
- Health check failures logged
- Instance marked as unhealthy
- New instance being spun up

### 5. Show recovery

Terminal check shows success now

Grafana remained UP since we have a second instance serving traffic.