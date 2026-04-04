import logging

import psutil
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)
metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics")
def metrics():
    try:
        cpu = psutil.cpu_percent()
        vm = psutil.virtual_memory()
        data = {
            "cpu_percent": cpu,
            "memory_percent": vm.percent,
            "memory_used_mb": round(vm.used / 1024 ** 2, 1),
            "memory_total_mb": round(vm.total / 1024 ** 2, 1),
        }
        logger.info("Metrics collected", extra={"component": "metrics", **data})
        return jsonify(data)
    except Exception as e:
        logger.error("Failed to collect metrics", extra={"component": "metrics", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500
