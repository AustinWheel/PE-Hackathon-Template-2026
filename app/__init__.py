import logging
import os
import sys
import time

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from pythonjsonlogger import json as json_logger


def setup_logging(app):
    formatter = json_logger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("app.log")
    file_handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.addHandler(stdout_handler)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def log_request():
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
        )

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

    with app.app_context():
        db.create_tables([User, Url, Event, Product], safe=True)

    register_routes(app)

    app._start_time = time.time()

    @app.route("/health")
    def health():
        from app.database import db

        health_data = {
            "status": "ok",
            "version": os.environ.get("APP_VERSION", "0.1.0"),
            "uptime_seconds": round(time.time() - app._start_time, 1),
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
