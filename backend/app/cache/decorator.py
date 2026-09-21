from collections.abc import Awaitable, Callable
from typing import TypeVar

import orjson

from app.cache.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def cached_json(
    key: str,
    ttl: int,
    producer: Callable[[], Awaitable[T]],
    *,
    skip_cache: bool = False,
) -> T:
    """Return a cached JSON value, otherwise run `producer` and store its result.

    Cache misses are never fatal: if Redis is unreachable the producer still runs.
    """
    redis = None
    if not skip_cache:
        try:
            redis = await get_redis()
            hit = await redis.get(key)
            if hit is not None:
                return orjson.loads(hit)
        except Exception as exc:  # noqa: BLE001 - cache must not break the request
            logger.warning("Redis read failed for %s: %s", key, exc)
            redis = None

    value = await producer()

    # Never persist an empty list: during upstream outages producers often
    # return [] and would otherwise poison a long TTL (city search looked like
    # "only popular cities exist").
    if redis is not None and value is not None and value != []:
        try:
            await redis.set(key, orjson.dumps(value), ex=ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis write failed for %s: %s", key, exc)

    return value
