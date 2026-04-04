import json
import os

from flask import Blueprint, jsonify, request

logs_bp = Blueprint("logs", __name__)

LOG_FILE = "app.log"


@logs_bp.route("/logs")
def view_logs():
    limit = request.args.get("limit", 50, type=int)
    level = request.args.get("level", None)

    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": [], "count": 0})

    with open(LOG_FILE) as f:
        lines = f.readlines()

    logs = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if level and entry.get("level") != level.upper():
            continue
        logs.append(entry)
        if len(logs) >= limit:
            break

    return jsonify({"logs": logs, "count": len(logs)})
