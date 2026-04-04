#!/usr/bin/env python3
"""
Chaos Monkey — automated failure injection.
Runs on a schedule, picks a random chaos endpoint, hits a random prod region.
Verifies that alerts fire as expected.
"""

import json
import os
import random
import time
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("chaos-monkey")

TARGETS = {
    "prod-nyc": os.environ.get("PROD_NYC_URL", ""),
    "prod-sfo": os.environ.get("PROD_SFO_URL", ""),
}
TARGETS = {k: v for k, v in TARGETS.items() if v}

ALERTMANAGER_URL = os.environ.get("ALERTMANAGER_URL", "http://localhost:9093")

# Low-impact chaos actions
CHAOS_ACTIONS = [
    {"path": "/chaos/error", "name": "single_error", "desc": "Trigger a single 500 error"},
    {"path": "/chaos/latency?delay=3", "name": "latency_3s", "desc": "Inject 3s latency"},
    {"path": "/chaos/cpu?duration=5&threads=2", "name": "cpu_spike_5s", "desc": "5s CPU spike with 2 threads"},
    {"path": "/chaos/error-flood?count=10", "name": "error_flood_10", "desc": "Generate 10 errors"},
]


def http_get(url):
    try:
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def check_alerts():
    """Check Alertmanager for active alerts."""
    try:
        status, data = http_get(f"{ALERTMANAGER_URL}/api/v2/alerts")
        if status == 200 and isinstance(data, list):
            firing = [a for a in data if a.get("status", {}).get("state") == "active"]
            return firing
    except Exception:
        pass
    return []


def run():
    if not TARGETS:
        logger.error("No targets configured.")
        return

    # Pick random target and action
    target_name = random.choice(list(TARGETS.keys()))
    target_url = TARGETS[target_name]
    action = random.choice(CHAOS_ACTIONS)

    logger.info(f"Chaos Monkey targeting {target_name}: {action['desc']}")

    # Execute chaos
    url = f"{target_url}{action['path']}"
    status, resp = http_get(url)
    logger.info(f"Chaos response: {status} - {json.dumps(resp)}")

    # Wait and check for alerts (only for flood actions)
    if "flood" in action["name"]:
        logger.info("Waiting 90s to check if alerts fire...")
        time.sleep(90)
        alerts = check_alerts()
        if alerts:
            logger.info(f"Active alerts found: {len(alerts)}")
            for a in alerts:
                labels = a.get("labels", {})
                logger.info(f"  Alert: {labels.get('alertname', '?')} severity={labels.get('severity', '?')}")
        else:
            logger.info("No active alerts (may not have breached threshold)")

    logger.info("Chaos Monkey run complete")


if __name__ == "__main__":
    run()
