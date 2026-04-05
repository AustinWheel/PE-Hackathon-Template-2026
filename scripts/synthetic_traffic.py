#!/usr/bin/env python3
"""
24/7 Synthetic traffic generator.
Simulates realistic usage patterns against prod and staging environments.
Generates ~5x traffic across all endpoints including error-producing actions.
Run as a systemd service on the monitoring Droplet.
"""

import json
import os
import random
import string
import time
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("synthetic-traffic")

TARGETS = {
    "prod-nyc": os.environ.get("PROD_NYC_URL", ""),
    "prod-sfo": os.environ.get("PROD_SFO_URL", ""),
    "staging": os.environ.get("STAGING_URL", ""),
}

# Remove empty targets
TARGETS = {k: v for k, v in TARGETS.items() if v}

INTERVAL = int(os.environ.get("INTERVAL_SECONDS", "3"))


def http(method, url, data=None):
    """Simple HTTP helper. Returns (status_code, response_body) or (0, error)."""
    try:
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# Track action counts for rolling stats
action_counts = {}


def record_action(action, status):
    """Record an action for rolling stats."""
    key = action
    if key not in action_counts:
        action_counts[key] = {"total": 0, "2xx": 0, "4xx": 0, "5xx": 0, "err": 0}
    action_counts[key]["total"] += 1
    if 200 <= status < 300:
        action_counts[key]["2xx"] += 1
    elif 400 <= status < 500:
        action_counts[key]["4xx"] += 1
    elif 500 <= status < 600:
        action_counts[key]["5xx"] += 1
    else:
        action_counts[key]["err"] += 1


def log_stats():
    """Log rolling stats every 50 cycles."""
    total_all = sum(v["total"] for v in action_counts.values())
    if total_all == 0:
        return
    logger.info("=== Rolling Action Stats ===")
    for action, counts in sorted(action_counts.items(), key=lambda x: -x[1]["total"]):
        pct = (counts["total"] / total_all) * 100
        s2 = (counts["2xx"] / counts["total"]) * 100 if counts["total"] else 0
        s4 = (counts["4xx"] / counts["total"]) * 100 if counts["total"] else 0
        s5 = (counts["5xx"] / counts["total"]) * 100 if counts["total"] else 0
        logger.info(
            f"  {action:30s} {pct:5.1f}% of traffic | "
            f"2xx: {s2:5.1f}%  4xx: {s4:5.1f}%  5xx: {s5:5.1f}%  "
            f"(n={counts['total']})"
        )
    logger.info(f"  {'TOTAL':30s} {total_all} requests")


def run_cycle(base_url, name):
    """Run one cycle of synthetic traffic against a target."""
    logger.info(f"[{name}] Starting traffic cycle")

    # --- Core health & monitoring (always run) ---

    # Health checks (x3 for load balancer coverage)
    for _ in range(3):
        status, _ = http("GET", f"{base_url}/health")
        record_action("GET /health", status)
    logger.info(f"[{name}] GET /health x3")

    status, _ = http("GET", f"{base_url}/metrics")
    record_action("GET /metrics", status)

    # --- User operations (x3 create cycles) ---

    user_ids = []
    for i in range(3):
        # List users
        status, _ = http("GET", f"{base_url}/users?per_page=10")
        record_action("GET /users", status)

        # Create user
        username = f"synth_{random_string()}"
        status, user = http("POST", f"{base_url}/users", {
            "username": username,
            "email": f"{username}@synthetic.test",
        })
        record_action("POST /users", status)
        if status == 201 and "id" in user:
            user_ids.append(user["id"])

            # Get user by ID
            status, _ = http("GET", f"{base_url}/users/{user['id']}")
            record_action("GET /users/:id", status)

            # Update user
            status, _ = http("PUT", f"{base_url}/users/{user['id']}", {
                "email": f"{username}_updated@synthetic.test",
            })
            record_action("PUT /users/:id", status)

    # --- Intentional user errors ---

    # Create user with missing fields (should 400)
    status, _ = http("POST", f"{base_url}/users", {"username": ""})
    record_action("POST /users (bad)", status)

    # Get non-existent user (should 404)
    status, _ = http("GET", f"{base_url}/users/999999")
    record_action("GET /users/:id (404)", status)

    # --- URL operations (x3 per user) ---

    url_ids = []
    short_codes = []
    for user_id in user_ids:
        for _ in range(2):
            status, url_data = http("POST", f"{base_url}/urls", {
                "user_id": user_id,
                "original_url": f"https://example.com/synth/{random_string(12)}",
                "title": f"Synthetic test {random_string(4)}",
            })
            record_action("POST /urls", status)
            if status == 201 and "id" in url_data:
                url_ids.append(url_data["id"])
                short_codes.append(url_data["short_code"])

        # List URLs for user
        status, _ = http("GET", f"{base_url}/urls?user_id={user_id}")
        record_action("GET /urls", status)

    # Get and update some URLs
    for url_id in url_ids[:3]:
        status, _ = http("GET", f"{base_url}/urls/{url_id}")
        record_action("GET /urls/:id", status)

        status, _ = http("PUT", f"{base_url}/urls/{url_id}", {
            "title": f"Updated {random_string(4)}",
        })
        record_action("PUT /urls/:id", status)

    # Deactivate one URL then try to redirect (should 410)
    if url_ids:
        deactivate_id = url_ids[-1]
        deactivate_code = short_codes[-1]
        status, _ = http("PUT", f"{base_url}/urls/{deactivate_id}", {"is_active": False})
        record_action("PUT /urls/:id (deactivate)", status)

        status, _ = http("GET", f"{base_url}/r/{deactivate_code}")
        record_action("GET /r/:code (410)", status)

    # --- Intentional URL errors ---

    # Create URL with missing user (should fail)
    status, _ = http("POST", f"{base_url}/urls", {
        "user_id": 999999,
        "original_url": "https://example.com/bad",
    })
    record_action("POST /urls (bad user)", status)

    # Get non-existent URL
    status, _ = http("GET", f"{base_url}/urls/999999")
    record_action("GET /urls/:id (404)", status)

    # Redirect with bad short code (should 404)
    status, _ = http("GET", f"{base_url}/r/NONEXIST")
    record_action("GET /r/:code (404)", status)

    # --- Redirect clicks (simulate real usage) ---

    for code in short_codes[:4]:
        status, _ = http("GET", f"{base_url}/r/{code}")
        record_action("GET /r/:code", status)

    # --- Events ---

    for _ in range(2):
        status, _ = http("GET", f"{base_url}/events?per_page=10")
        record_action("GET /events", status)

    # --- Products ---

    status, _ = http("GET", f"{base_url}/products")
    record_action("GET /products", status)

    # --- Alerts ---

    # List alerts
    status, _ = http("GET", f"{base_url}/alerts")
    record_action("GET /alerts", status)

    status, _ = http("GET", f"{base_url}/alerts?status=firing")
    record_action("GET /alerts (filtered)", status)

    # Create and manage an alert
    status, alert = http("POST", f"{base_url}/alerts", {
        "alert_name": f"synth_test_{random_string(4)}",
        "severity": random.choice(["warning", "critical"]),
        "summary": "Synthetic traffic test alert",
        "source": name,
    })
    record_action("POST /alerts", status)

    if status == 201 and "id" in alert:
        # Acknowledge it
        status, _ = http("PUT", f"{base_url}/alerts/{alert['id']}", {
            "status": "acknowledged",
            "acknowledged_by": "synthetic-traffic",
            "notes": "Auto-acknowledged by synthetic traffic generator",
        })
        record_action("PUT /alerts/:id (ack)", status)

        # Resolve it
        status, _ = http("PUT", f"{base_url}/alerts/{alert['id']}", {
            "status": "resolved",
        })
        record_action("PUT /alerts/:id (resolve)", status)

    # --- Logs endpoint ---

    status, _ = http("GET", f"{base_url}/logs?limit=10")
    record_action("GET /logs", status)

    status, _ = http("GET", f"{base_url}/logs?limit=5&level=ERROR")
    record_action("GET /logs (errors)", status)

    logger.info(f"[{name}] Cycle complete")


def main():
    if not TARGETS:
        logger.error("No targets configured. Set PROD_NYC_URL, PROD_SFO_URL, or STAGING_URL.")
        return

    logger.info(f"Starting synthetic traffic against: {list(TARGETS.keys())}")
    logger.info(f"Interval: {INTERVAL}s")

    cycle_count = 0
    while True:
        for tgt_name, url in TARGETS.items():
            try:
                run_cycle(url, tgt_name)
            except Exception as e:
                logger.error(f"[{tgt_name}] Cycle failed: {e}")

        cycle_count += 1
        if cycle_count % 50 == 0:
            log_stats()

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
