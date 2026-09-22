import hashlib
import json

import httpx

from app.cache.redis import get_redis

SEARXNG_URL = "http://searxng:8080"
CACHE_TTL = 3600


async def search(
    query: str,
    top_k: int = 5,
    snippet_len: int = 200,
) -> list[dict]:
    redis = await get_redis()

    cache_key = (
        "searxng:"
        + hashlib.sha256(
            f"{query}:{top_k}:{snippet_len}".encode()
        ).hexdigest()
    )

    cached = await redis.get(cache_key)

    if cached:
        return json.loads(cached)

    resp = httpx.get(
        f"{SEARXNG_URL}/search",
        params={"q": query, "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", [])[:top_k]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": (item.get("content") or "")[:snippet_len],
        })

    await redis.set(
        cache_key,
        json.dumps(results, ensure_ascii=False),
        ex=CACHE_TTL,
    )

    return results