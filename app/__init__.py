import logging
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, request
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
        app.logger.info("Request received", extra={
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        })

    @app.after_request
    def log_response(response):
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

    register_routes(app)

    @app.route("/health")
    def health():
        app.logger.info("Health check", extra={"component": "health"})
        return jsonify(status="ok")

    return app
