# Incident Runbook

When an alert fires, open this page. Find the alert name. Follow the steps.

## Quick Access

| System | URL |
|---|---|
| Grafana | http://143.198.173.164:3000 |
| Prometheus | http://143.198.173.164:9090 |
| Loki | http://143.198.173.164:3100 |
| Prod App | https://pe-hackathon-hni9m.ondigitalocean.app |
| Staging App | https://pe-hackathon-staging-stj5i.ondigitalocean.app |
| DO Dashboard | https://cloud.digitalocean.com |

### Quick Health Check
```bash
curl -s https://pe-hackathon-hni9m.ondigitalocean.app/health | python3 -m json.tool
```

## Alert: Service Down

**Severity:** Critical | **Meaning:** The app is not responding to health checks.

### Diagnose
1. Check Grafana Overview dashboard — is the Production panel red?
2. Check App Platform logs:
   ```bash
   doctl apps logs 20ade529-aeb0-49f4-be02-779b07d6734e --follow
   ```
3. Check if the database is reachable:
   ```bash
   curl -s https://pe-hackathon-hni9m.ondigitalocean.app/health | python3 -c "import json,sys; print(json.load(sys.stdin).get('database'))"
   ```

### Recover
- **If app crashed:** App Platform auto-restarts. Wait 1-2 minutes.
- **If deploy broke it:** Rollback via DO Dashboard → App → Activity → Rollback.
- **If DB is down:** Check DO Dashboard → Databases → hackathon-db status.

### Force Redeploy
```bash
doctl apps create-deployment 20ade529-aeb0-49f4-be02-779b07d6734e --wait
```

## Alert: High Error Rate (>10%)

**Severity:** Warning | **Meaning:** More than 10% of requests are returning 5xx errors.

### Diagnose
1. Grafana → Errors row → "5xx Errors by Endpoint" to find the failing endpoint
2. Loki query: `{job="flask-app", environment="prod"} | json | level="ERROR"`
3. Check if chaos monkey caused it: `{job="flask-app"} | json | component="chaos"`

### Recover
- **Chaos monkey:** Transient, resolves in 2-5 minutes.
- **Real errors:** Check stack trace in Loki, fix code, push to main.
- **DB related:** Check database connectivity.

## Alert: Critical Error Rate (>25%)

**Severity:** Critical | **Meaning:** Possible outage. Escalate immediately.

Same diagnosis as High Error Rate. Additionally:
1. Check if a bad deploy just went out — rollback if so
2. Check database and Redis health
3. If Redis is down, app degrades gracefully but DB load spikes

## Alert: High P95 Latency (>2s)

**Severity:** Warning | **Meaning:** The slowest 5% of requests take over 2 seconds.

### Diagnose
1. Grafana → Latency → "P95 Latency by Endpoint" to find the slow endpoint
2. Check CPU/Memory panels — instance saturated?
3. Check In-Flight Requests — queuing?

### Recover
- **CPU-bound:** Scale instances or upgrade size
- **DB-bound:** Check if Redis is down (cache miss = more DB queries)
- **Chaos latency:** Transient, resolves when delay ends

## Alert: High CPU (>80%) / High Memory (>85%)

**Severity:** Warning

### Diagnose
1. Is chaos monkey running a CPU spike? Check chaos logs.
2. Is traffic unusually high? Check Traffic panel.
3. Is memory growing over time (leak)? Check Process Memory panel.

### Recover
- **Temporary spike:** Wait for it to pass
- **Sustained CPU:** Add instances in `.do/app.yaml`, redeploy
- **Memory leak:** Redeploy (triggers fresh instances)

## Chaos Monkey Management

```bash
# Check status
ssh root@143.198.173.164 "systemctl list-timers chaos-monkey.timer"

# View recent actions
ssh root@143.198.173.164 "journalctl -u chaos-monkey --no-pager -n 20"

# Disable
ssh root@143.198.173.164 "systemctl stop chaos-monkey.timer"

# Re-enable
ssh root@143.198.173.164 "systemctl start chaos-monkey.timer"

# Manual trigger
ssh root@143.198.173.164 "systemctl start chaos-monkey.service"
```

## Escalation

1. Check Grafana dashboards and Loki logs
2. Infrastructure issue → check DO Dashboard for platform status
3. Code issue → check recent commits, rollback if needed
4. Data issue → check managed database dashboard for connection limits, disk usage
