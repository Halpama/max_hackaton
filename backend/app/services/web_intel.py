"""SearXNG-backed discovery digests for trip curation (thin, cacheable)."""

from __future__ import annotations

import re

from app.clients import searxng
from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm import INTEREST_LABELS

logger = get_logger(__name__)

_HOTEL_RE = re.compile(
    r"\b(отель|гостиниц|хостел|апарт|hotel|hostel|apart)\w*",
    re.IGNORECASE,
)


async def discover_city_hints(
    city: str,
    interests: list[str],
    *,
    max_queries: int = 2,
) -> tuple[list[str], str | None]:
    """Return (place-like titles, short digest) for curation / memory.

    Stores only thin titles + a short digest — not full page HTML. Failures
    degrade to empty so Redis-less / SearXNG-down still generates routes.
    """
    if not settings.searxng_enabled:
        return [], None

    interest_labels = [
        INTEREST_LABELS.get(i, i) for i in (interests or ["sights"])
    ][:3]
    queries = [
        f"лучшие места {city} {' '.join(interest_labels)} 2025",
        f"необычные локации {city} куда сходить",
    ][:max_queries]

    titles: list[str] = []
    snippets: list[str] = []
    seen: set[str] = set()

    for query in queries:
        try:
            results = await searxng.search(query, top_k=5, snippet_len=160)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SearXNG discover failed for %s: %s", query, exc)
            continue

        for item in results:
            title = str(item.get("title") or "").strip()
            content = str(item.get("content") or "").strip()
            if not title or _HOTEL_RE.search(title):
                continue
            key = title.casefold()
            if key in seen:
                continue
            seen.add(key)
            titles.append(title[:120])
            if content and not _HOTEL_RE.search(content):
                snippets.append(f"{title}: {content[:140]}")
            if len(titles) >= 12:
                break
        if len(titles) >= 12:
            break

    digest = None
    if snippets:
        digest = " | ".join(snippets[:4])[:800]
    return titles, digest
