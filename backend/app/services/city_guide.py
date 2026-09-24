"""City overview for the «О поездке» tab — profiles + live Wikipedia/SearXNG."""

from __future__ import annotations

import asyncio
from datetime import date
from urllib.parse import quote

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.clients.climate import seasonality_scores
from app.core.config import settings
from app.core.logging import get_logger
from app.data.russian_cities import normalize_city_key
from app.services import web_intel

logger = get_logger(__name__)

MONTHS = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)

PROFILES: dict[str, dict[str, object]] = {
    "санкт-петербург": {
        "type": "Музеи, вода и парадные фасады",
        "summary": "Длинные прогулки, музеи, набережные и исторический центр.",
        "history": "Основан Петром I в 1703 году; более двух столетий был столицей Российской империи.",
        "highlights": [
            "Белые ночи и длинный световой день",
            "Музеи лучше планировать с учётом выходных",
            "В центре удобно пешком и на метро",
        ],
        "seasonality": [2, 2, 3, 4, 5, 5, 5, 5, 4, 3, 2, 2],
    },
    "москва": {
        "type": "История и современная городская жизнь",
        "summary": "Музеи, гастрономия, театры и маршруты по разным районам.",
        "history": "Впервые упоминается в 1147 году. Вокруг Кремля вырос главный политический и культурный центр страны.",
        "highlights": [
            "Закладывайте время на переезды между районами",
            "Центр хорош для прогулок в тёплый сезон",
            "Билеты в музеи и театры лучше брать заранее",
        ],
        "seasonality": [2, 3, 4, 5, 5, 5, 5, 5, 4, 3, 2, 2],
    },
    "казань": {
        "type": "Культурный перекрёсток Волги",
        "summary": "Кремль, татарская кухня, набережные и смешение архитектурных традиций.",
        "history": "Крупный город Волжской Булгарии; с 1552 года — в составе Русского государства.",
        "highlights": [
            "Татарская кухня в центре",
            "Кремль и Старо-Татарская слобода удобно объединить",
            "Летом прогулки комфортнее утром и вечером",
        ],
        "seasonality": [2, 3, 4, 5, 5, 5, 5, 4, 4, 3, 2, 2],
    },
    "сочи": {
        "type": "Море у подножия гор",
        "summary": "Побережье, парки и выезды в горы в одном маршруте.",
        "history": "Вырос из черноморского укрепления XIX века и курортной инфраструктуры XX века.",
        "highlights": [
            "Побережье и Красная Поляна — разные планы на день",
            "Летом учитывайте жару и пробки",
            "После дождя горные тропы скользкие",
        ],
        "seasonality": [3, 3, 4, 4, 5, 5, 5, 5, 5, 4, 4, 3],
    },
    "калининград": {
        "type": "Балтика и европейское наследие",
        "summary": "Остров Канта, старые районы, музеи и короткие поездки к морю.",
        "history": "Основан как Кёнигсберг в XIII веке; после Второй мировой — центр Калининградской области.",
        "highlights": [
            "Погода у Балтики меняется быстро",
            "На побережье удобно выделить отдельный день",
            "Янтарь и рыба — часть локальной идентичности",
        ],
        "seasonality": [2, 2, 3, 4, 5, 5, 5, 5, 4, 3, 2, 2],
    },
}


def _level(score: int) -> str:
    if score >= 5:
        return "Пик"
    if score >= 4:
        return "Высокий"
    if score >= 3:
        return "Средний"
    return "Спокойный"


def _default_profile(city: str) -> dict[str, object]:
    return {
        "type": city,
        "summary": f"Маршрут по {city}: главные места, прогулки и локальный ритм.",
        "history": "",
        "highlights": [
            "Проверьте часы работы перед визитом",
            "Оставляйте запас времени на дорогу",
        ],
        "seasonality": [2, 2, 3, 4, 5, 5, 5, 5, 4, 3, 2, 2],
    }


async def fetch_wikipedia_city(city: str) -> dict[str, str | None]:
    """Thin Wikipedia summary — extract + optional thumb. Cached in Redis."""
    q = (city or "").strip()
    if not q:
        return {}

    cache_key = f"wiki:city:v1:{normalize_city_key(q)}"

    async def produce() -> dict[str, str | None]:
        url = (
            "https://ru.wikipedia.org/api/rest_v1/page/summary/"
            + quote(q, safe="")
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "2RIST/1.0 (hackathon; city-guide)",
                    },
                )
                if response.status_code == 404:
                    return {}
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Wikipedia summary failed for %s: %s", q, exc)
            return {}

        extract = str(data.get("extract") or "").strip()
        description = str(data.get("description") or "").strip()
        thumb = None
        thumbnail = data.get("thumbnail") or {}
        if isinstance(thumbnail, dict):
            thumb = str(thumbnail.get("source") or "") or None
        if thumb:
            thumb = thumb.replace(
                "https://thumb.wikimedia.org/", "https://upload.wikimedia.org/"
            ).split("?", 1)[0]

        return {
            "extract": extract[:900] if extract else None,
            "description": description[:160] if description else None,
            "image_url": thumb,
            "page_url": str(data.get("content_urls", {}).get("desktop", {}).get("page") or "")
            or None,
        }

    return await cached_json(cache_key, keys.TTL_GEONAME, produce)


async def build_city_guide(
    city: str,
    trip_date: date,
    *,
    lat: float | None = None,
    lon: float | None = None,
    digest: str | None = None,
    hints: list[str] | None = None,
) -> dict:
    """Assemble overview: Wikipedia + climate seasonality (+ curated fallback)."""
    key = normalize_city_key(city)
    profile = dict(PROFILES.get(key) or _default_profile(city))

    wiki_task = asyncio.create_task(fetch_wikipedia_city(city))
    live_task = asyncio.create_task(
        web_intel.discover_city_hints(city, ["sights", "walks"], max_queries=1)
    ) if settings.searxng_enabled and (not digest or not hints) else None
    climate_task = (
        asyncio.create_task(seasonality_scores(float(lat), float(lon)))
        if lat is not None and lon is not None
        else None
    )

    wiki = await wiki_task
    if wiki.get("description") and (
        key not in PROFILES or not str(profile.get("type") or "").strip()
    ):
        profile["type"] = wiki["description"]
    if wiki.get("extract"):
        # Prefer encyclopedic extract for «о городе»; keep curated when richer.
        existing = str(profile.get("history") or "")
        extract = str(wiki["extract"])
        if not existing or len(extract) > len(existing) + 40:
            profile["history"] = extract
        if key not in PROFILES or len(str(profile.get("summary") or "")) < 40:
            # First sentence of extract as lead.
            lead = extract.split(". ", 1)[0].strip()
            if lead and not lead.endswith("."):
                lead += "."
            if lead:
                profile["summary"] = lead[:280]

    live_hints, live_digest = await live_task if live_task is not None else ([], None)
    _ = live_hints

    tip_digest = digest or live_digest
    highlights = [str(h) for h in (profile.get("highlights") or []) if h][:4]

    if tip_digest and not str(profile.get("summary") or "").strip():
        profile["summary"] = tip_digest.split("|", 1)[0].strip()[:280]

    climate_scores: list[int] | None = (
        await climate_task if climate_task is not None else None
    )

    scores = list(
        climate_scores
        or profile.get("seasonality")
        or [2, 2, 3, 4, 5, 5, 5, 5, 4, 3, 2, 2]
    )
    trip_month = trip_date.month
    seasonality = [
        {
            "month": index + 1,
            "label": MONTHS[index],
            "score": int(score),
            "level": _level(int(score)),
            "is_trip_month": index + 1 == trip_month,
        }
        for index, score in enumerate(scores)
    ]

    return {
        "type": str(profile.get("type") or city),
        "summary": str(profile.get("summary") or ""),
        "history": str(profile.get("history") or ""),
        "highlights": highlights,
        "trip_month": trip_month,
        "trip_month_label": MONTHS[trip_month - 1],
        "seasonality": seasonality,
        "seasonality_source": "climate" if climate_scores else "profile",
        "image_url": wiki.get("image_url"),
        "source_url": wiki.get("page_url"),
        "source_name": "Википедия" if wiki.get("extract") else None,
    }
