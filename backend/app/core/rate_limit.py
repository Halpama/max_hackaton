"""Fixed-window request counter for /api/v1.

Keys on the MAX user when initData resolves, otherwise on the client IP.
Fails open: a Redis outage must never take the API down with it.
"""
import time

from app.cache.redis import get_redis
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import resolve_user

logger = get_logger(__name__)

RATE_LIMIT_CODE = "rate_limited"


def limit_for(method: str, path: str) -> int | None:
    """Requests per window for a path, or None when the path is exempt."""
    if not path.startswith("/api/v1"):
        return None
    # The MAX platform calls the webhook from its own infra — keying that on
    # an IP would throttle everyone behind one egress address.
    if path.startswith("/api/v1/bot"):
        return None
    if method == "POST" and path.rstrip("/") == "/api/v1/trips":
        return settings.rate_limit_trip_max
    # A PATCH regenerates the route just like POST /trips — same quota burn.
    if method == "PATCH" and path.startswith("/api/v1/trips/"):
        return settings.rate_limit_trip_max
    if path.startswith("/api/v1/geo"):
        return settings.rate_limit_geo_max
    return settings.rate_limit_max_requests


def client_key(authorization: str | None, client_host: str | None) -> str:
    try:
        user = resolve_user(authorization)
        return f"u:{user.max_user_id}"
    except Exception:  # noqa: BLE001 - unauthenticated traffic falls back to IP
        return f"ip:{client_host or 'unknown'}"


async def allow_request(
    method: str, path: str, authorization: str | None, client_host: str | None
) -> bool:
    if not settings.rate_limit_enabled:
        return True
    limit = limit_for(method, path)
    if limit is None:
        return True

    window = settings.rate_limit_window_seconds
    bucket = f"rl:{client_key(authorization, client_host)}:{int(time.time() // window)}"
    try:
        redis = await get_redis()
        count = await redis.incr(bucket)
        if count == 1:
            await redis.expire(bucket, window * 2)
        return count <= limit
    except Exception as exc:  # noqa: BLE001 - fail open on Redis trouble
        logger.warning("Rate limit check failed (allowing request): %s", exc)
        return True
