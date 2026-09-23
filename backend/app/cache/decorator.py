from collections.abc import Awaitable, Callable
import asyncio
import uuid
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

    if redis is None:
        return await producer()

    lock_key = f"{key}:lock"
    lock_token = uuid.uuid4().hex
    acquired = False
    try:
        acquired = bool(
            await redis.set(lock_key, lock_token, ex=keys.TTL_CACHE_LOCK, nx=True)
        )
    except Exception as exc:  # noqa: BLE001 - cache must not block the producer
        logger.warning("Redis lock acquisition failed for %s: %s", key, exc)
        return await producer()

    if not acquired:
        try:
            for _ in range(30):
                await asyncio.sleep(0.1)
                hit = await redis.get(key)
                if hit is not None:
                    return orjson.loads(hit)
        except Exception as exc:  # noqa: BLE001 - cache must not block the producer
            logger.warning("Redis lock wait failed for %s: %s", key, exc)
        logger.warning("Cache lock wait timed out for %s", key)

    try:
        value = await producer()
    finally:
        if acquired:
            try:
                await redis.eval(
                    "if redis.call('get', KEYS[1]) == ARGV[1] then "
                    "return redis.call('del', KEYS[1]) else return 0 end",
                    1,
                    lock_key,
                    lock_token,
                )
            except Exception as exc:  # noqa: BLE001 - lock cleanup is best-effort
                logger.warning("Redis lock cleanup failed for %s: %s", key, exc)

    # Never persist an empty list: during upstream outages producers often
    # return [] and would otherwise poison a long TTL (city search looked like
    # "only popular cities exist").
    if value is not None and value != []:
        try:
            await redis.set(key, orjson.dumps(value), ex=ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis write failed for %s: %s", key, exc)

    return value
