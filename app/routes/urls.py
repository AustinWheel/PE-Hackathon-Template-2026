import json
import logging
import string
import random
from datetime import datetime

from flask import Blueprint, jsonify, request, redirect

from app.models.url import Url
from app.models.user import User
from app.models.event import Event

logger = logging.getLogger(__name__)
urls_bp = Blueprint("urls", __name__)


def _generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _url_to_dict(url):
    return {
        "id": url.id,
        "user_id": url.user_id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "created_at": url.created_at.isoformat() if isinstance(url.created_at, datetime) else str(url.created_at),
        "updated_at": url.updated_at.isoformat() if isinstance(url.updated_at, datetime) else str(url.updated_at),
    }


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    data = request.get_json()
    if not data or "original_url" not in data or "user_id" not in data:
        logger.warning("Invalid create URL request", extra={
            "component": "urls",
            "error": "missing original_url or user_id",
        })
        return jsonify({"error": "original_url and user_id are required"}), 400

    try:
        user = User.get_by_id(data["user_id"])
    except User.DoesNotExist:
        logger.warning("User not found", extra={
            "component": "urls",
            "user_id": data["user_id"],
        })
        return jsonify({"error": "User not found"}), 404

    short_code = _generate_short_code()
    now = datetime.utcnow()

    url = Url.create(
        user=user,
        short_code=short_code,
        original_url=data["original_url"],
        title=data.get("title", ""),
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    Event.create(
        url=url,
        user=user,
        event_type="created",
        timestamp=now,
        details=json.dumps({
            "short_code": short_code,
            "original_url": data["original_url"],
        }),
    )

    logger.info("URL created", extra={
        "component": "urls",
        "short_code": short_code,
        "user_id": user.id,
    })

    return jsonify(_url_to_dict(url)), 201


@urls_bp.route("/urls")
def list_urls():
    from app.cache import cache_get, cache_set

    user_id = request.args.get("user_id", type=int)
    cache_key = f"urls:list:{user_id or 'all'}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("URLs listed (cache hit)", extra={"component": "urls", "user_id": user_id})
        return jsonify(cached)

    query = Url.select()
    if user_id:
        query = query.where(Url.user == user_id)

    results = [_url_to_dict(u) for u in query]
    cache_set(cache_key, results, ttl=30)
    logger.info("URLs listed (cache miss)", extra={
        "component": "urls",
        "count": len(results),
        "user_id": user_id,
    })
    return jsonify(results)


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        logger.warning("URL not found", extra={"component": "urls", "url_id": url_id})
        return jsonify({"error": "URL not found"}), 404

    logger.info("URL retrieved", extra={"component": "urls", "url_id": url_id})
    return jsonify(_url_to_dict(url))


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        logger.warning("URL not found for update", extra={"component": "urls", "url_id": url_id})
        return jsonify({"error": "URL not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "title" in data:
        url.title = data["title"]
    if "is_active" in data:
        url.is_active = data["is_active"]
    if "original_url" in data:
        url.original_url = data["original_url"]

    url.updated_at = datetime.utcnow()
    url.save()

    logger.info("URL updated", extra={"component": "urls", "url_id": url_id})
    return jsonify(_url_to_dict(url))


@urls_bp.route("/r/<short_code>")
def redirect_short(short_code):
    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        logger.warning("Short code not found", extra={
            "component": "redirect",
            "short_code": short_code,
        })
        return jsonify({"error": "Short URL not found"}), 404

    if not url.is_active:
        logger.warning("Inactive URL accessed", extra={
            "component": "redirect",
            "short_code": short_code,
        })
        return jsonify({"error": "This URL has been deactivated"}), 410

    Event.create(
        url=url,
        user=url.user,
        event_type="click",
        timestamp=datetime.utcnow(),
        details=json.dumps({
            "short_code": short_code,
            "referrer": request.referrer,
            "user_agent": request.user_agent.string,
        }),
    )

    logger.info("Redirect", extra={
        "component": "redirect",
        "short_code": short_code,
        "destination": url.original_url,
    })

    return redirect(url.original_url)
