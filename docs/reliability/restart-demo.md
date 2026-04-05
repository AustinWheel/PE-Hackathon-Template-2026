# Service Restart Demo Script

## What we're demonstrating
When the app fails health checks, App Platform automatically kills and restarts the instance. We trigger this with the `/chaos/health-fail` endpoint, which makes `/health` return 503 for 60 seconds. App Platform polls `/health` every 10s — after 3 consecutive failures (30s), it restarts the instance.

## Setup

Open 3 windows:

1. **Terminal** — health check loop
2. **Browser** — DigitalOcean App Platform dashboard → pe-hackathon → Runtime Logs
3. **Browser** — Grafana dashboard at http://143.198.173.164:3000/d/overview/

## Steps

### 1. Show steady state (~10s)

In the terminal, start a health check loop:
```bash
while true; do
  echo "$(date +%H:%M:%S) $(curl -s -o /dev/null -w '%{http_code}' https://pe-hackathon-hni9m.ondigitalocean.app/health)"
  sleep 2
done
```

You should see `200` every 2 seconds. Show this for a few seconds.

### 2. Trigger the failure

In a second terminal tab:
```bash
curl -s https://pe-hackathon-hni9m.ondigitalocean.app/chaos/health-fail?duration=60 | python3 -m json.tool
```

### 3. Show health checks failing (~15s)

Switch back to the first terminal. You'll start seeing `503` responses mixed in (the load balancer routes some requests to the failing instance, some to the healthy one).

### 4. Show App Platform restarting (~15s)

Switch to the DO dashboard Runtime Logs. You'll see:
- Health check failures logged
- Instance marked as unhealthy
- New instance being spun up

### 5. Show recovery (~15s)

Switch back to the terminal. The `503` responses stop and all requests return `200` again as the new instance comes online.

Show Grafana briefly — the Production panel stays green because the second instance kept serving traffic throughout.

### 6. End

Stop the loop with Ctrl+C.

## Key points to narrate

- "We have 2 instances behind the load balancer"
- "I'm triggering a health check failure on one instance"
- "App Platform detects the failure and kills the unhealthy instance"
- "The other instance keeps serving traffic — zero downtime"
- "A new instance boots and takes over"
