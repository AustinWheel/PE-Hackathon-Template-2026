import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.event import Event
from app.models.url import Url
from app.models.user import User

logger = logging.getLogger(__name__)
events_bp = Blueprint("events", __name__)


def _event_to_dict(event):
    details = event.details
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": event.id,
        "url_id": event.url_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
        "details": details,
    }


@events_bp.route("/events")
def list_events():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    url_id = request.args.get("url_id", type=int)
    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")

    query = Event.select().order_by(Event.id)
    if url_id:
        query = query.where(Event.url == url_id)
    if user_id:
        query = query.where(Event.user == user_id)
    if event_type:
        query = query.where(Event.event_type == event_type)

    events = query.paginate(page, per_page)

    result = [_event_to_dict(e) for e in events]
    logger.info("Events listed", extra={"component": "events", "count": len(result), "page": page})
    return jsonify(result)


@events_bp.route("/events", methods=["POST"])
def create_event():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body is required"}), 400

    errors = {}
    if "event_type" not in data:
        errors["event_type"] = "event_type is required"
    elif not isinstance(data["event_type"], str):
        errors["event_type"] = "event_type must be a string"

    if "url_id" not in data:
        errors["url_id"] = "url_id is required"
    if "user_id" not in data:
        errors["user_id"] = "user_id is required"

    # Validate details is a dict if provided
    if "details" in data and data["details"] is not None:
        if not isinstance(data["details"], dict):
            errors["details"] = "details must be a JSON object"

    if errors:
        logger.warning("Invalid event data", extra={"component": "events", "errors": errors})
        return jsonify({"errors": errors}), 400

    # Validate foreign keys exist
    try:
        url = Url.get_by_id(data["url_id"])
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404

    try:
        user = User.get_by_id(data["user_id"])
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404

    details = data.get("details", {})
    if isinstance(details, dict):
        details = json.dumps(details)

    event = Event.create(
        url=url,
        user=user,
        event_type=data["event_type"],
        timestamp=datetime.utcnow(),
        details=details,
    )

    logger.info("Event created", extra={"component": "events", "event_id": event.id})
    return jsonify(_event_to_dict(event)), 201
