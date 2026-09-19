import asyncio
from collections.abc import AsyncIterator

import orjson

from app.cache import keys
from app.cache.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Progress data is short-lived; a generation never runs longer than a few minutes.
EVENT_TTL = 3600


async def publish(trip_id: object, event: dict) -> None:
    """Append an event to the replay log and fan it out to live subscribers."""
    try:
        redis = await get_redis()
        seq = await redis.incr(f"trip:{trip_id}:seq")
        payload = orjson.dumps({**event, "seq": seq}).decode()

        pipe = redis.pipeline()
        pipe.rpush(keys.trip_progress_log(trip_id), payload)
        pipe.expire(keys.trip_progress_log(trip_id), EVENT_TTL)
        pipe.expire(f"trip:{trip_id}:seq", EVENT_TTL)
        pipe.publish(keys.trip_progress_channel(trip_id), payload)
        await pipe.execute()
    except Exception as exc:  # noqa: BLE001 - progress is best-effort
        logger.warning("Could not publish progress for %s: %s", trip_id, exc)


async def history(trip_id: object) -> list[dict]:
    try:
        redis = await get_redis()
        raw = await redis.lrange(keys.trip_progress_log(trip_id), 0, -1)
        return [orjson.loads(item) for item in raw]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read progress history for %s: %s", trip_id, exc)
        return []


async def stream(trip_id: object) -> AsyncIterator[dict]:
    """Yield every event for a trip: the backlog first, then live updates.

    Subscribing before replaying the backlog avoids a gap; duplicates are removed
    with the monotonic `seq` each event carries.
    """
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(keys.trip_progress_channel(trip_id))

    seen: set[int] = set()
    try:
        for event in await history(trip_id):
            seq = event.get("seq", 0)
            if seq in seen:
                continue
            seen.add(seq)
            yield event
            if event.get("type") in {"done", "error"}:
                return

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message is None:
                # Emit a heartbeat so proxies do not drop an idle SSE connection.
                yield {"type": "ping"}
                await asyncio.sleep(0)
                continue

            event = orjson.loads(message["data"])
            seq = event.get("seq", 0)
            if seq in seen:
                continue
            seen.add(seq)
            yield event
            if event.get("type") in {"done", "error"}:
                return
    finally:
        try:
            await pubsub.unsubscribe(keys.trip_progress_channel(trip_id))
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
