import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.alert import Alert

logger = logging.getLogger(__name__)
alerts_bp = Blueprint("alerts", __name__)


def _alert_to_dict(alert):
    return {
        "id": alert.id,
        "alert_name": alert.alert_name,
        "severity": alert.severity,
        "status": alert.status,
        "summary": alert.summary,
        "source": alert.source,
        "notes": alert.notes,
        "fired_at": alert.fired_at.isoformat() if hasattr(alert.fired_at, "isoformat") else str(alert.fired_at),
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at and hasattr(alert.acknowledged_at, "isoformat") else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at and hasattr(alert.resolved_at, "isoformat") else None,
        "acknowledged_by": alert.acknowledged_by,
    }


@alerts_bp.route("/alerts")
def list_alerts():
    query = Alert.select().order_by(Alert.fired_at.desc())

    status = request.args.get("status")
    if status:
        query = query.where(Alert.status == status)

    severity = request.args.get("severity")
    if severity:
        query = query.where(Alert.severity == severity)

    result = [_alert_to_dict(a) for a in query]
    logger.info("Alerts listed", extra={"component": "alerts", "count": len(result)})
    return jsonify(result)


@alerts_bp.route("/alerts/<int:alert_id>")
def get_alert(alert_id):
    try:
        alert = Alert.get_by_id(alert_id)
    except Alert.DoesNotExist:
        return jsonify({"error": "Alert not found"}), 404

    return jsonify(_alert_to_dict(alert))


@alerts_bp.route("/alerts", methods=["POST"])
def create_alert():
    data = request.get_json()
    if not data or "alert_name" not in data:
        return jsonify({"error": "alert_name is required"}), 400

    alert = Alert.create(
        alert_name=data["alert_name"],
        severity=data.get("severity", "warning"),
        status="firing",
        summary=data.get("summary", ""),
        source=data.get("source", ""),
        notes=data.get("notes", ""),
        fired_at=datetime.utcnow(),
    )

    logger.warning("Alert fired", extra={
        "component": "alerts",
        "alert_name": alert.alert_name,
        "severity": alert.severity,
    })
    return jsonify(_alert_to_dict(alert)), 201


@alerts_bp.route("/alerts/<int:alert_id>", methods=["PUT"])
def update_alert(alert_id):
    try:
        alert = Alert.get_by_id(alert_id)
    except Alert.DoesNotExist:
        return jsonify({"error": "Alert not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    now = datetime.utcnow()

    if "status" in data:
        new_status = data["status"]
        if new_status not in ("firing", "acknowledged", "resolved"):
            return jsonify({"error": "status must be firing, acknowledged, or resolved"}), 400

        alert.status = new_status
        if new_status == "acknowledged":
            alert.acknowledged_at = now
            alert.acknowledged_by = data.get("acknowledged_by", "unknown")
        elif new_status == "resolved":
            alert.resolved_at = now

    if "notes" in data:
        # Append notes with timestamp
        existing = alert.notes or ""
        new_note = f"[{now.isoformat()}] {data['notes']}"
        alert.notes = f"{existing}\n{new_note}".strip()

    alert.save()

    logger.info("Alert updated", extra={
        "component": "alerts",
        "alert_id": alert_id,
        "status": alert.status,
    })
    return jsonify(_alert_to_dict(alert))
