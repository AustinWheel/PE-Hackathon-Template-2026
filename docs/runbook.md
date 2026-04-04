# Incident Runbook

When an alert fires at 3 AM, open this page. Find the alert name. Follow the steps. Don't think — just do.

## Access

| System | URL | Credentials |
|--------|-----|-------------|
| Prod NYC | https://pe-hackathon-muy5v.ondigitalocean.app | — |
| Prod SFO | https://pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app | — |
| Staging | https://pe-hackathon-staging-f28oj.ondigitalocean.app | — |
| Grafana | http://143.198.173.164:3000 | admin / admin |
| Prometheus | http://143.198.173.164:9090 | — |
| Alertmanager | http://143.198.173.164:9093 | — |
| Loki | http://143.198.173.164:3100 | — |
| DO Dashboard | https://cloud.digitalocean.com/apps | DO account |

### App IDs (for doctl)
```
prod-nyc:  1c0e8082-1afa-4fa0-a941-4877f46f6a48
prod-sfo:  baf4705a-d8f2-4b58-b3bd-c1f8779a22e5
staging:   5e2a377f-8cdd-4d0c-a0af-676d7c6ed8f7
postgres:  dacc1fe1-631a-4746-9bd1-606294a1dc32
```

---

## Alert: ServiceDown

**What it means:** Prometheus cannot reach an app for over 1 minute. The alert annotation tells you which region.

**Steps:**

1. Which region is down? Check the alert's `region` label.
2. Check if the app responds:
   ```bash
   curl https://pe-hackathon-muy5v.ondigitalocean.app/health      # NYC
   curl https://pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app/health  # SFO
   ```
3. If no response, check DO App Platform:
   ```bash
   doctl apps list-deployments <APP_ID> | head -5
   doctl apps logs <APP_ID> --type=run | tail -30
   ```
4. If the app crashed, DO auto-restarts it. Wait 2 minutes and re-check.
5. If stuck in a crash loop, check deploy logs:
   ```bash
   doctl apps logs <APP_ID> --type=deploy | tail -30
   ```
6. If a bad deploy caused it, force a rebuild from last known good:
   ```bash
   doctl apps create-deployment <APP_ID> --force-rebuild
   ```
7. If the database is down:
   ```bash
   doctl databases get dacc1fe1-631a-4746-9bd1-606294a1dc32
   ```

**Acknowledge:** `curl -X PUT <app-url>/alerts/<id> -H 'Content-Type: application/json' -d '{"status":"acknowledged","acknowledged_by":"your-name","notes":"Investigating"}'`

**Resolved when:** `/health` returns 200 and Prometheus target shows "up".

---

## Alert: RegionDown

**What it means:** Fewer than 2 production regions are healthy for over 2 minutes.

**Steps:**

1. Check both regions:
   ```bash
   curl -s https://pe-hackathon-muy5v.ondigitalocean.app/health
   curl -s https://pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app/health
   ```
2. Check Prometheus targets:
   ```bash
   curl -s http://143.198.173.164:9090/api/v1/targets | python3 -c "
   import json, sys
   for t in json.load(sys.stdin)['data']['activeTargets']:
       print(f\"{t['labels']['job']} health={t['health']}\")
   "
   ```
3. If one region is down, the other is still serving traffic. Focus on restoring the downed region.
4. Follow the ServiceDown steps for the affected region.
5. If both regions are down, check the database first — it's the shared dependency.

**Resolved when:** Both prod regions show "up" in Prometheus.

---

## Alert: HighErrorRate

**What it means:** Over 10% of requests are returning 5xx in a region over a 2-minute window.

**Steps:**

1. Check Loki for errors (use the deep link in the Discord alert, or):
   - Grafana → Explore → Loki → `{job="flask-app", region="<region>"} |= "ERROR"`
2. Or via the app:
   ```bash
   curl "<app-url>/logs?level=ERROR&limit=20"
   ```
3. Look at the `path` and `component` fields to identify which endpoint is broken.
4. Check Grafana dashboard — filter by the affected region:
   - Is it one endpoint or all of them?
   - Did it start after a deploy?
   - Is the database healthy?
5. If it started after a deploy: revert or fix and push.
6. If Redis is down, caching degrades gracefully but DB load increases — check Redis:
   ```bash
   doctl databases list --format Name,Status
   ```

**Resolved when:** Error rate drops below 10% on Grafana.

---

## Alert: HighLatencyP95

**What it means:** P95 response time is above 2 seconds for over 2 minutes.

**Steps:**

1. Check Grafana Latency panel — which endpoints are slow?
2. Check if it's a CPU issue: Grafana Saturation panel.
3. If CPU is high, autoscaling should kick in (3→15 instances). Wait 2-3 minutes.
4. If it's database-related, check for slow queries in logs.
5. Check if Redis is healthy — cache misses cause DB load.

**Resolved when:** P95 latency drops below 2s.

---

## Quick Health Check (copy-paste this)

```bash
echo "=== Prod NYC ===" && curl -s https://pe-hackathon-muy5v.ondigitalocean.app/health | python3 -m json.tool
echo "=== Prod SFO ===" && curl -s https://pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app/health | python3 -m json.tool
echo "=== Staging ===" && curl -s https://pe-hackathon-staging-f28oj.ondigitalocean.app/health | python3 -m json.tool
echo "=== Prometheus Targets ===" && curl -s http://143.198.173.164:9090/api/v1/targets | python3 -c "import json,sys; [print(f\"{t['labels']['job']} {t['health']}\") for t in json.load(sys.stdin)['data']['activeTargets']]"
echo "=== Active Alerts ===" && curl -s http://143.198.173.164:9093/api/v2/alerts | python3 -c "import json,sys; alerts=json.load(sys.stdin); print(f'{len(alerts)} active') if alerts else print('none')"
```

## Chaos Monkey

The chaos monkey runs every 30 minutes on the monitoring Droplet. If you're investigating an alert and suspect it's from the chaos monkey:

```bash
ssh root@143.198.173.164 "journalctl -u chaos-monkey --no-pager -n 10"
```

To disable temporarily:
```bash
ssh root@143.198.173.164 "systemctl stop chaos-monkey.timer"
```

To re-enable:
```bash
ssh root@143.198.173.164 "systemctl start chaos-monkey.timer"
```

## Escalation

1. Check Discord for messages from teammates
2. Check DigitalOcean status page: https://status.digitalocean.com
3. If monitoring Droplet is down:
   ```bash
   ssh root@143.198.173.164
   cd /root/monitoring && docker compose ps
   docker compose restart
   ```
