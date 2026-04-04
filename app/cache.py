import json
import os
import logging

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    """Lazy-init Redis connection. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis
        _redis_client = redis.from_url(redis_url, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info("Redis connected", extra={"component": "cache"})
        return _redis_client
    except Exception as e:
        logger.warning("Redis unavailable, caching disabled", extra={
            "component": "cache", "error": str(e),
        })
        return None


def cache_get(key):
    """Get a value from cache. Returns None on miss or if Redis is down."""
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception:
        pass
    return None


def cache_set(key, value, ttl=30):
    """Set a value in cache with TTL in seconds."""
    r = get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete_pattern(pattern):
    """Delete all keys matching a pattern."""
    r = get_redis()
    if r is None:
        return
    try:
        for key in r.scan_iter(match=pattern):
            r.delete(key)
    except Exception:
        pass
