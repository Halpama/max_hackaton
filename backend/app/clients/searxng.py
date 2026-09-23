import hashlib
import json

import httpx

from app.cache.redis import get_redis
from app.core.config import settings
from app.core.errors import UpstreamError
from app.core.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL = 3600


async def search(
    query: str,
    top_k: int = 5,
    snippet_len: int = 200,
) -> list[dict]:
    cache_key = (
        "searxng:"
        + hashlib.sha256(
            f"{query}:{top_k}:{snippet_len}".encode()
        ).hexdigest()
    )

    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as exc:  # noqa: BLE001 - search still works without cache
        logger.warning("SearXNG cache read failed: %s", exc)
        redis = None

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            resp = await client.get(
                f"{settings.searxng_url.rstrip('/')}/search",
                params={"q": query, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise UpstreamError(f"SearXNG search failed: {exc}") from exc

    results = []
    for item in data.get("results", [])[:top_k]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": (item.get("content") or "")[:snippet_len],
        })

    try:
        redis = await get_redis()
        await redis.set(
            cache_key,
            json.dumps(results, ensure_ascii=False),
            ex=CACHE_TTL,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SearXNG cache write failed: %s", exc)

    return results
