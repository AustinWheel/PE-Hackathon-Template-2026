import json
import logging
import time
import threading
import urllib.request
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.alert import Alert

logger = logging.getLogger(__name__)
chaos_bp = Blueprint("chaos", __name__)

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489813519560868031/VnmqUl_1xxH5XaDNC6m0JuxEk0YX-6-yw5qtLkXKXIgSxNX-BYfgaP6AM7EuQO7cmK6B"


@chaos_bp.route("/chaos/error")
def chaos_error():
    """Simulate a 500 Internal Server Error."""
    status_code = request.args.get("status", 500, type=int)
    logger.error(
        "Chaos: simulated error triggered",
        extra={"component": "chaos", "status_code": status_code},
    )
    return jsonify({"error": "Chaos simulated failure", "status": status_code}), status_code


@chaos_bp.route("/chaos/cpu")
def chaos_cpu():
    """Spike CPU for a given number of seconds (default 10, max 60)."""
    duration = min(request.args.get("duration", 10, type=int), 60)
    threads = min(request.args.get("threads", 4, type=int), 8)

    def burn():
        end = time.time() + duration
        while time.time() < end:
            _ = sum(i * i for i in range(10000))

    logger.warning(
        "Chaos: CPU spike started",
        extra={"component": "chaos", "duration": duration, "threads": threads},
    )
    for _ in range(threads):
        t = threading.Thread(target=burn, daemon=True)
        t.start()

    return jsonify({
        "chaos": "cpu_spike",
        "duration_seconds": duration,
        "threads": threads,
        "status": "started",
    })


@chaos_bp.route("/chaos/latency")
def chaos_latency():
    """Simulate a slow response (default 5s, max 30s)."""
    delay = min(request.args.get("delay", 5, type=int), 30)
    logger.warning(
        "Chaos: artificial latency injected",
        extra={"component": "chaos", "delay_seconds": delay},
    )
    time.sleep(delay)
    return jsonify({"chaos": "latency", "delay_seconds": delay})


@chaos_bp.route("/chaos/health-fail")
def chaos_health_fail():
    """Make /health return 503 for a duration, triggering App Platform to restart the instance."""
    from flask import current_app
    duration = min(request.args.get("duration", 60, type=int), 300)

    current_app._health_fail_until = time.time() + duration

    logger.critical(
        "Chaos: health check will fail for %ds",
        duration,
        extra={"component": "chaos", "duration": duration},
    )

    Alert.create(
        alert_name="ServiceDown",
        severity="critical",
        status="firing",
        summary=f"Health check failing for {duration}s via chaos endpoint",
        source="chaos/health-fail",
        fired_at=datetime.utcnow(),
    )

    return jsonify({"chaos": "health_fail", "duration_seconds": duration, "status": "health check will return 503"})


@chaos_bp.route("/chaos/kill")
def chaos_kill():
    """Kill this instance's process. App Platform will restart it automatically."""
    import os
    import signal

    delay = min(request.args.get("delay", 2, type=int), 10)

    logger.critical(
        "Chaos: process will be killed in %ds",
        delay,
        extra={"component": "chaos", "delay": delay},
    )

    Alert.create(
        alert_name="ProcessKill",
        severity="critical",
        status="firing",
        summary=f"Process killed via chaos endpoint (delay={delay}s)",
        source="chaos/kill",
        fired_at=datetime.utcnow(),
    )

    def _kill():
        time.sleep(delay)
        os.kill(os.getpid(), signal.SIGTERM)

    t = threading.Thread(target=_kill, daemon=True)
    t.start()

    return jsonify({
        "chaos": "kill",
        "delay_seconds": delay,
        "pid": os.getpid(),
        "status": f"process will terminate in {delay}s",
    })


@chaos_bp.route("/chaos/error-flood")
def chaos_error_flood():
    """Generate a burst of 500 errors to trigger 'High Error Rate' alerts."""
    count = min(request.args.get("count", 50, type=int), 200)
    for i in range(count):
        logger.error(
            "Chaos: simulated error %d/%d",
            i + 1,
            count,
            extra={"component": "chaos", "error_index": i + 1, "total": count},
        )

    Alert.create(
        alert_name="HighErrorRate",
        severity="warning",
        status="firing",
        summary=f"Error flood: {count} errors generated via chaos endpoint",
        source="chaos/error-flood",
        fired_at=datetime.utcnow(),
    )

    return jsonify({
        "chaos": "error_flood",
        "errors_generated": count,
        "status": "complete",
    }), 500


@chaos_bp.route("/chaos/critical")
def chaos_critical():
    """One-hit endpoint that sends a critical alert straight to Discord.

    Hit this once to test the Discord integration — no waiting for
    Prometheus thresholds or timing windows.
    """
    message = request.args.get(
        "msg", "Critical failure detected — database connection pool exhausted"
    )

    logger.critical(
        "CRITICAL FAILURE: %s",
        message,
        extra={"component": "chaos", "severity": "critical"},
    )

    Alert.create(
        alert_name="CriticalFailure",
        severity="critical",
        status="firing",
        summary=message,
        source="chaos/critical",
        fired_at=datetime.utcnow(),
    )

    content = (
        "\U0001f6a8 **CRITICAL ALERT — FIRING**\n\n"
        f"**Alert:** CriticalFailure\n"
        f"**Severity:** critical\n"
        f"**Message:** {message}\n"
        f"**Source:** /chaos/critical endpoint\n\n"
        "_Sent by Flask Alerting System_"
    )

    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        DISCORD_WEBHOOK,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "FlaskAlertSystem/1.0",
        },
    )
    try:
        urllib.request.urlopen(req)
        discord_sent = True
    except Exception as e:
        logger.error("Failed to send to Discord: %s", e)
        discord_sent = False

    return jsonify({
        "chaos": "critical_failure",
        "message": message,
        "discord_notified": discord_sent,
    }), 500
