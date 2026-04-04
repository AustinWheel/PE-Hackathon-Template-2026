#!/usr/bin/env python3
"""
24/7 Synthetic traffic generator.
Simulates realistic usage patterns against prod and staging environments.
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

INTERVAL = int(os.environ.get("INTERVAL_SECONDS", "5"))


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
        return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def run_cycle(base_url, name):
    """Run one cycle of synthetic traffic against a target."""
    logger.info(f"[{name}] Starting traffic cycle")

    # 1. Health check
    status, _ = http("GET", f"{base_url}/health")
    logger.info(f"[{name}] GET /health -> {status}")

    # 2. List users
    status, data = http("GET", f"{base_url}/users?per_page=5")
    logger.info(f"[{name}] GET /users -> {status}")

    # 3. Create a user
    username = f"synth_{random_string()}"
    status, user = http("POST", f"{base_url}/users", {
        "username": username,
        "email": f"{username}@synthetic.test",
    })
    logger.info(f"[{name}] POST /users -> {status}")

    if status != 201 or "id" not in user:
        logger.warning(f"[{name}] Failed to create user, skipping URL creation")
        return

    user_id = user["id"]

    # 4. Create a short URL
    status, url_data = http("POST", f"{base_url}/urls", {
        "user_id": user_id,
        "original_url": f"https://example.com/synth/{random_string(12)}",
        "title": f"Synthetic test {random_string(4)}",
    })
    logger.info(f"[{name}] POST /urls -> {status}")

    if status != 201 or "short_code" not in url_data:
        return

    # 5. List URLs
    status, _ = http("GET", f"{base_url}/urls?user_id={user_id}")
    logger.info(f"[{name}] GET /urls?user_id={user_id} -> {status}")

    # 6. Get URL details
    status, _ = http("GET", f"{base_url}/urls/{url_data['id']}")
    logger.info(f"[{name}] GET /urls/{url_data['id']} -> {status}")

    # 7. Simulate a redirect click (won't actually follow, just triggers the event)
    short_code = url_data["short_code"]
    status, _ = http("GET", f"{base_url}/r/{short_code}")
    logger.info(f"[{name}] GET /r/{short_code} -> {status}")

    # 8. List events
    status, _ = http("GET", f"{base_url}/events?per_page=5")
    logger.info(f"[{name}] GET /events -> {status}")

    # 9. Check metrics
    status, _ = http("GET", f"{base_url}/metrics")
    logger.info(f"[{name}] GET /metrics -> {status}")

    logger.info(f"[{name}] Cycle complete")


def main():
    if not TARGETS:
        logger.error("No targets configured. Set PROD_NYC_URL, PROD_SFO_URL, or STAGING_URL.")
        return

    logger.info(f"Starting synthetic traffic against: {list(TARGETS.keys())}")
    logger.info(f"Interval: {INTERVAL}s")

    while True:
        for name, url in TARGETS.items():
            try:
                run_cycle(url, name)
            except Exception as e:
                logger.error(f"[{name}] Cycle failed: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
