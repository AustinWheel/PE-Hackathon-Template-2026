# Service Restart Demo Script

## What we're demonstrating
When an app instance crashes, Docker's `restart: always` policy automatically restarts it. We kill the main process inside a container to simulate a crash — Docker detects the exit and spins up a replacement. The other instances keep serving traffic through the nginx load balancer, so there's zero downtime.

## Setup

Open a terminal in the project root with the local stack running:
```bash
docker compose up -d
```

## Steps

### 1. Show all 3 instances running

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep app
```

Expected output — all 3 instances up:
```
hackathon-app3-1    Up 5 minutes
hackathon-app2-1    Up 5 minutes
hackathon-app1-1    Up 5 minutes
```

### 2. Verify health works

```bash
curl -s http://localhost:8080/health | python3 -m json.tool
```

### 3. Crash an instance

Kill the main process (PID 1) inside app1. This simulates an unexpected crash:
```bash
docker exec hackathon-app1-1 /bin/sh -c 'kill 1'
```

### 4. Show it restarted automatically

Run immediately after the kill:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep app
```

Expected output — app1 restarted, others unaffected:
```
hackathon-app3-1    Up 5 minutes
hackathon-app2-1    Up 5 minutes
hackathon-app1-1    Up 2 seconds
```

### 5. Health still works (zero downtime)

```bash
curl -s http://localhost:8080/health | python3 -m json.tool
```

Nginx routed traffic to app2 and app3 while app1 was restarting. No requests were dropped.

## Key points to narrate

- "We have 3 app instances behind nginx, all with `restart: always`"
- "I'm killing the main process inside one container to simulate a crash"
- "Docker detects the crash and restarts it automatically — here it is, 2 seconds old"
- "The other two instances kept serving traffic the whole time — zero downtime"
- "This is the same behavior in production: App Platform restarts crashed containers automatically"
