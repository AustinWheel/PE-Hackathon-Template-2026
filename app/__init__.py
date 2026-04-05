import logging
import os
import sys
import time
import uuid

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from pythonjsonlogger import json as json_logger

# Unique per-process instance ID
INSTANCE_ID = os.environ.get("APP_INSTANCE_ID", str(uuid.uuid4())[:8])


class RegionFilter(logging.Filter):
    """Injects instance_id, region, and environment into every log record."""

    def filter(self, record):
        record.instance_id = INSTANCE_ID
        record.region = os.environ.get("APP_REGION", "local")
        record.environment = os.environ.get("APP_ENVIRONMENT", "dev")
        return True


def setup_logging(app):
    formatter = json_logger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )

    region_filter = RegionFilter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(region_filter)

    app.logger.handlers.clear()
    app.logger.addHandler(stdout_handler)
    app.logger.setLevel(logging.INFO)

    # Loki handler — only active when LOKI_URL is set
    from app.loki_handler import create_loki_handler
    loki_handler = create_loki_handler(formatter=formatter)
    if loki_handler:
        loki_handler.addFilter(region_filter)
        app.logger.addHandler(loki_handler)
        app.logger.info("Loki log shipping enabled", extra={"component": "logging"})

    @app.before_request
    def log_request():
        from app.routes.prom_metrics import REQUESTS_IN_FLIGHT
        REQUESTS_IN_FLIGHT.inc()
        g.start_time = time.time()
        app.logger.info("Request received", extra={
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        })

    @app.after_request
    def log_response(response):
        from app.routes.prom_metrics import (
            REQUEST_COUNT,
            REQUEST_LATENCY,
            ERROR_COUNT,
            REQUESTS_IN_FLIGHT,
        )
        REQUESTS_IN_FLIGHT.dec()

        elapsed = time.time() - g.get("start_time", time.time())
        endpoint = request.path

        # Record metrics for Prometheus
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(elapsed)

        if response.status_code >= 500:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
            ).inc()

        app.logger.info("Request completed", extra={
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
        })
        return response


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # Store instance metadata on app for access in routes
    app.config["APP_INSTANCE_ID"] = INSTANCE_ID
    app.config["APP_REGION"] = os.environ.get("APP_REGION", "local")
    app.config["APP_ENVIRONMENT"] = os.environ.get("APP_ENVIRONMENT", "dev")

    setup_logging(app)

    from app.database import init_db
    from app.routes import register_routes

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee
    from app.database import db
    from app.models.user import User
    from app.models.url import Url
    from app.models.event import Event
    from app.models.product import Product
    from app.models.alert import Alert
    from app.models.loadtest import LoadTestResult

    with app.app_context():
        db.create_tables([User, Url, Event, Product, Alert, LoadTestResult], safe=True)

    # Rate limiting
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=os.environ.get("REDIS_URL", "memory://"),
            default_limits=["2000 per minute"],
        )
        app.limiter = limiter
    except ImportError:
        app.logger.warning("flask-limiter not installed, rate limiting disabled")

    register_routes(app)

    # Exempt monitoring endpoints from rate limiting (after routes are registered)
    if hasattr(app, "limiter"):
        for endpoint_name in ["health", "prometheus_metrics", "metrics", "view_logs"]:
            fn = app.view_functions.get(endpoint_name)
            if fn:
                app.limiter.exempt(fn)

    app._start_time = time.time()

    @app.route("/health")
    def health():
        from app.database import db

        health_data = {
            "status": "ok",
            "version": os.environ.get("APP_VERSION", "0.1.0"),
            "uptime_seconds": round(time.time() - app._start_time, 1),
            "region": app.config["APP_REGION"],
            "environment": app.config["APP_ENVIRONMENT"],
            "instance_id": app.config["APP_INSTANCE_ID"],
        }

        # Check database connectivity
        try:
            db.connect(reuse_if_open=True)
            db.execute_sql("SELECT 1")
            health_data["database"] = "connected"
        except Exception as e:
            health_data["status"] = "degraded"
            health_data["database"] = f"error: {str(e)}"
            app.logger.error("Health check: DB unreachable", extra={
                "component": "health", "error": str(e),
            })
            return jsonify(health_data), 503

        app.logger.info("Health check", extra={"component": "health"})
        return jsonify(health_data)

    return app
