# Service Restart Demo Script

## What we're demonstrating
When an app instance crashes, App Platform automatically restarts it. We use `/chaos/kill` to terminate the process — App Platform detects the container died and spins up a replacement. The other instance keeps serving traffic, so there's zero downtime.

## Setup

Open 2 windows:

1. **Terminal** — health check loop showing instance IDs
2. **Browser** — DigitalOcean App Platform dashboard → pe-hackathon → Runtime Logs

## Steps

### 1. Show both instances are healthy (~10s)

Run this to see which instances are serving:
```bash
while true; do
  curl -s https://pe-hackathon-hni9m.ondigitalocean.app/health | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f\"{d['instance_id']}  uptime={d['uptime_seconds']}s  status={d['status']}\")"
  sleep 2
done
```

You'll see two different `instance_id` values alternating (load balancer round-robins). Both show high uptime.

### 2. Kill one instance

In a second terminal:
```bash
curl -s https://pe-hackathon-hni9m.ondigitalocean.app/chaos/kill | python3 -m json.tool
```

Note the `pid` in the response — that process will terminate in 2 seconds.

### 3. Show recovery (~30s)

Switch back to the first terminal. You'll see:
- One of the `instance_id` values disappears temporarily
- All requests still return `200` (the surviving instance handles everything)
- A **new** `instance_id` appears with `uptime_seconds` near 0 — that's the restarted instance

### 4. Show DO Runtime Logs

Switch to the App Platform dashboard. The Runtime Logs will show:
- The killed instance's gunicorn worker exiting
- A new container starting up with fresh gunicorn worker PIDs

## Key points to narrate

- "We have 2 instances behind the load balancer — here are their instance IDs"
- "I'm killing one instance's process"
- "The load balancer routes all traffic to the surviving instance — no downtime"
- "App Platform detects the crash and starts a new instance automatically"
- "Here's the new instance with a fresh ID and zero uptime"
