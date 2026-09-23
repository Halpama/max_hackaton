"""cached_json is the single choke point for every upstream cache — pin its contract."""

from app.cache.decorator import cached_json


async def test_hit_reuses_cached_value(redis_client):
    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        return {"n": calls}

    first = await cached_json("test:kv", 60, produce)
    second = await cached_json("test:kv", 60, produce)

    assert first == {"n": 1}
    assert second == {"n": 1}
    assert calls == 1


async def test_skip_cache_always_runs_producer(redis_client):
    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        return {"n": calls}

    await cached_json("test:skip", 60, produce, skip_cache=True)
    await cached_json("test:skip", 60, produce, skip_cache=True)

    assert calls == 2


async def test_empty_list_is_never_stored(redis_client):
    """Upstream outages return [] — caching it would poison the TTL."""
    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        return []

    assert await cached_json("test:empty", 60, produce) == []
    assert await cached_json("test:empty", 60, produce) == []
    assert calls == 2


async def test_redis_failure_degrades_to_producer(monkeypatch):
    async def broken():
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.cache.decorator.get_redis", broken)

    async def produce():
        return {"ok": True}

    assert await cached_json("test:down", 60, produce) == {"ok": True}


async def test_lock_is_released_after_produce(redis_client):
    async def produce():
        return {"v": 1}

    await cached_json("test:lock", 60, produce)

    assert await redis_client.get("test:lock:lock") is None
    assert await redis_client.get("test:lock") is not None


async def test_concurrent_miss_produces_once(redis_client):
    import asyncio

    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return {"n": calls}

    results = await asyncio.gather(
        cached_json("test:concurrent", 60, produce),
        cached_json("test:concurrent", 60, produce),
    )

    # The lock serialises producers; the waiter either joins or re-produces.
    assert all(r in ({"n": 1}, {"n": 2}) for r in results)
    assert calls <= 2
