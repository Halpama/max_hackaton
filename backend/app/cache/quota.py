from app.cache import keys
from app.cache.redis import get_redis
from app.core.config import settings
from app.core.errors import QuotaExceededError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def consume_opentripmap_call() -> int:
    """Count one OpenTripMap call against today's free-tier budget.

    Raises QuotaExceededError once the daily limit is reached so we fail loudly
    instead of silently getting empty responses from the provider.
    """
    try:
        redis = await get_redis()
        used = await redis.incr(keys.otm_quota())
        if used == 1:
            await redis.expire(keys.otm_quota(), 2 * 86_400)
    except QuotaExceededError:
        raise
    except Exception as exc:  # noqa: BLE001 - never block on a bookkeeping failure
        logger.warning("Could not track OpenTripMap quota: %s", exc)
        return 0

    if used > settings.opentripmap_daily_limit:
        raise QuotaExceededError(
            f"OpenTripMap daily limit reached ({settings.opentripmap_daily_limit} requests)"
        )

    return used


async def opentripmap_usage() -> int:
    try:
        redis = await get_redis()
        return int(await redis.get(keys.otm_quota()) or 0)
    except Exception:  # noqa: BLE001
        return 0
