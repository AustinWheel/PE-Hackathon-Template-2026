import csv
import io
import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

logger = logging.getLogger(__name__)
users_bp = Blueprint("users", __name__)


def _user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else str(user.created_at),
    }


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_upload_users():
    if "file" not in request.files:
        logger.warning("Bulk upload missing file", extra={"component": "users"})
        return jsonify({"error": "file field is required"}), 400

    file = request.files["file"]
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)
    rows = list(reader)

    with db.atomic():
        for row in rows:
            User.create(
                username=row["username"],
                email=row["email"],
                created_at=row.get("created_at", datetime.utcnow()),
            )

    logger.info("Bulk users imported", extra={"component": "users", "count": len(rows)})
    return jsonify({"count": len(rows)}), 201


@users_bp.route("/users")
def list_users():
    from app.cache import cache_get, cache_set

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    cache_key = f"users:list:{page}:{per_page}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("Users listed (cache hit)", extra={"component": "users", "page": page})
        return jsonify(cached)

    query = User.select().order_by(User.id)
    total = query.count()
    users = query.paginate(page, per_page)

    result = [_user_to_dict(u) for u in users]
    cache_set(cache_key, result, ttl=30)
    logger.info("Users listed (cache miss)", extra={"component": "users", "count": len(result), "page": page})
    return jsonify(result)


@users_bp.route("/users/<int:user_id>")
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        logger.warning("User not found", extra={"component": "users", "user_id": user_id})
        return jsonify({"error": "User not found"}), 404

    logger.info("User retrieved", extra={"component": "users", "user_id": user_id})
    return jsonify(_user_to_dict(user))


@users_bp.route("/users", methods=["POST"])
def create_user():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body is required"}), 400

    errors = {}
    if "username" not in data:
        errors["username"] = "username is required"
    elif not isinstance(data["username"], str):
        errors["username"] = "username must be a string"

    if "email" not in data:
        errors["email"] = "email is required"
    elif not isinstance(data["email"], str):
        errors["email"] = "email must be a string"
    elif not EMAIL_REGEX.match(data["email"]):
        errors["email"] = "email must be a valid email address"

    if errors:
        logger.warning("Invalid user data", extra={"component": "users", "errors": errors})
        return jsonify({"errors": errors}), 400

    # Duplicate prevention
    existing = User.select().where(
        (User.username == data["username"]) | (User.email == data["email"])
    ).first()
    if existing:
        logger.warning("Duplicate user", extra={"component": "users", "username": data["username"]})
        return jsonify({"error": "A user with that username or email already exists"}), 409

    user = User.create(
        username=data["username"],
        email=data["email"],
        created_at=datetime.utcnow(),
    )

    logger.info("User created", extra={"component": "users", "user_id": user.id})
    return jsonify(_user_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        logger.warning("User not found for update", extra={"component": "users", "user_id": user_id})
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body is required"}), 400

    if "username" in data:
        if not isinstance(data["username"], str):
            return jsonify({"errors": {"username": "username must be a string"}}), 400
        # Check uniqueness against other users
        conflict = User.select().where(
            (User.username == data["username"]) & (User.id != user_id)
        ).first()
        if conflict:
            return jsonify({"error": "A user with that username already exists"}), 409
        user.username = data["username"]
    if "email" in data:
        if not isinstance(data["email"], str):
            return jsonify({"errors": {"email": "email must be a string"}}), 400
        # Check uniqueness against other users
        conflict = User.select().where(
            (User.email == data["email"]) & (User.id != user_id)
        ).first()
        if conflict:
            return jsonify({"error": "A user with that email already exists"}), 409
        user.email = data["email"]

    user.save()

    logger.info("User updated", extra={"component": "users", "user_id": user_id})
    return jsonify(_user_to_dict(user))


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    from app.models.url import Url
    from app.models.event import Event

    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        logger.warning("User not found for delete", extra={"component": "users", "user_id": user_id})
        return jsonify({"error": "User not found"}), 404

    # Delete related records first (FK constraints)
    # 1. Delete events owned by this user
    Event.delete().where(Event.user == user).execute()
    # 2. Delete events on this user's URLs (from other users clicking them)
    user_urls = Url.select(Url.id).where(Url.user == user)
    Event.delete().where(Event.url.in_(user_urls)).execute()
    # 3. Now safe to delete the URLs
    Url.delete().where(Url.user == user).execute()
    user.delete_instance()

    logger.info("User deleted", extra={"component": "users", "user_id": user_id})
    return jsonify({"message": "User deleted"}), 200
