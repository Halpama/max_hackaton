"""City name suggestions via Open-Meteo Geocoding (free, keyless).

Only trip-worthy cities are returned — the same class of destinations the
pipeline can enrich via KudaGo / OpenTripMap. Villages that merely share a
famous name (Казань-Омга in Кировская область) are filtered out.
"""

from __future__ import annotations

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.clients.kudago import CITY_SLUGS
from app.core.logging import get_logger

logger = get_logger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

#: Admin seats and large towns. Plain PPL without population = village noise.
_ADMIN_FEATURE_CODES = frozenset({"PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4"})
#: Below this a PPL is a village / suburb, not a trip destination.
_MIN_CITY_POPULATION = 50_000

#: Shown when the field is focused with an empty query.
POPULAR_CITIES: tuple[dict[str, str], ...] = (
    {"name": "Москва", "subtitle": "Россия", "label": "Москва"},
    {"name": "Санкт-Петербург", "subtitle": "Россия", "label": "Санкт-Петербург"},
    {"name": "Казань", "subtitle": "Татарстан, Россия", "label": "Казань"},
    {"name": "Сочи", "subtitle": "Краснодарский край, Россия", "label": "Сочи"},
    {"name": "Екатеринбург", "subtitle": "Свердловская область, Россия", "label": "Екатеринбург"},
    {"name": "Нижний Новгород", "subtitle": "Россия", "label": "Нижний Новгород"},
    {"name": "Калининград", "subtitle": "Россия", "label": "Калининград"},
    {"name": "Владивосток", "subtitle": "Россия", "label": "Владивосток"},
)

#: Last-resort coords when OpenTripMap and Open-Meteo are both unreachable.
_KNOWN_COORDS: dict[str, tuple[float, float]] = {
    "москва": (55.7558, 37.6173),
    "санкт-петербург": (59.9311, 30.3609),
    "петербург": (59.9311, 30.3609),
    "казань": (55.7963, 49.1088),
    "сочи": (43.6028, 39.7342),
    "екатеринбург": (56.8389, 60.6057),
    "нижний новгород": (56.2965, 43.9361),
    "калининград": (54.7104, 20.4522),
    "владивосток": (43.1155, 131.8855),
    "махачкала": (42.9849, 47.5047),
    "ульяновск": (54.3142, 48.4031),
}

_KNOWN_CITY_NAMES = frozenset(CITY_SLUGS) | {
    city["name"].casefold() for city in POPULAR_CITIES
} | frozenset(_KNOWN_COORDS)

#: Rough mainland + Kaliningrad + Far East envelope. Rejects Africa / Americas
#: hits when a latinised LLM geoQuery confuses OpenTripMap.
_RU_LAT_MIN, _RU_LAT_MAX = 41.0, 82.0
_RU_LON_MIN, _RU_LON_MAX = 19.0, 191.0


def in_russia(lat: float, lon: float) -> bool:
    return _RU_LAT_MIN <= lat <= _RU_LAT_MAX and _RU_LON_MIN <= lon <= _RU_LON_MAX


def _result_row(item: dict) -> dict[str, str] | None:
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    admin = str(item.get("admin1") or "").strip()
    country = str(item.get("country") or "").strip() or "Россия"
    parts = [part for part in (admin, country) if part and part.casefold() != name.casefold()]
    subtitle = ", ".join(parts) if parts else country
    return {"name": name, "subtitle": subtitle, "label": name}


def is_trip_city(item: dict) -> bool:
    """Keep destinations the itinerary pipeline can actually fill with places."""
    code = str(item.get("feature_code") or "")
    raw_pop = item.get("population")
    try:
        population = int(raw_pop) if raw_pop is not None else None
    except (TypeError, ValueError):
        population = None

    name = str(item.get("name") or "").strip().casefold()

    # Namesakes of famous cities that are actually villages have no population.
    if code == "PPL" and population is None:
        return False

    if name in _KNOWN_CITY_NAMES:
        return code in _ADMIN_FEATURE_CODES or (
            population is not None and population >= _MIN_CITY_POPULATION
        )

    if code in _ADMIN_FEATURE_CODES:
        return population is None or population >= 10_000

    if code == "PPL":
        return population is not None and population >= _MIN_CITY_POPULATION

    return False


def _pick_best_result(results: list[dict], *, russia_only: bool) -> dict | None:
    ranked = sorted(
        (
            item
            for item in results
            if (not russia_only or str(item.get("country_code") or "").upper() == "RU")
            and is_trip_city(item)
        ),
        key=lambda item: int(item.get("population") or 0),
        reverse=True,
    )
    if ranked:
        return ranked[0]

    # Softer pass: any RU hit with coords when filters are too strict.
    for item in results:
        if russia_only and str(item.get("country_code") or "").upper() != "RU":
            continue
        lat, lon = item.get("latitude"), item.get("longitude")
        if lat is None or lon is None:
            continue
        if russia_only and not in_russia(float(lat), float(lon)):
            continue
        return item
    return None


async def resolve_coords(name: str) -> dict[str, float | str]:
    """Resolve a city name to lat/lon, preferring Russian destinations.

    Used when `api.opentripmap.com` is unreachable, and as the primary geocoder
    so an LLM latinisation cannot land the itinerary in Africa.
    """
    q = (name or "").strip()
    if not q:
        raise ValueError("empty city name")

    cache_key = f"geo:coords:ru:v2:{q.casefold()}"

    async def produce() -> dict[str, float | str]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    GEOCODE_URL,
                    params={
                        "name": q,
                        "count": 10,
                        "language": "ru",
                        "countryCode": "RU",
                        "format": "json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
            best = _pick_best_result(payload.get("results") or [], russia_only=True)
            if best is not None:
                lat, lon = float(best["latitude"]), float(best["longitude"])
                if in_russia(lat, lon):
                    return {
                        "lat": lat,
                        "lon": lon,
                        "name": str(best.get("name") or q),
                        "country": "RU",
                    }
        except Exception as exc:  # noqa: BLE001 - fall through to table
            logger.warning("Open-Meteo geocode failed for %s: %s", q, exc)

        known = _KNOWN_COORDS.get(q.casefold())
        if known is not None:
            return {"lat": known[0], "lon": known[1], "name": q, "country": "RU"}

        raise LookupError(f"City not found: {q}")

    return await cached_json(cache_key, keys.TTL_GEONAME, produce)


async def suggest_cities(query: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Return city suggestions for the trip destination field."""
    q = (query or "").strip()
    if len(q) < 2:
        return list(POPULAR_CITIES)[:limit]

    cache_key = f"geo:city:ru:v4:{q.lower()}:{limit}"

    async def produce() -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    GEOCODE_URL,
                    params={
                        "name": q,
                        # Over-fetch: most hits for famous names are villages.
                        "count": max(limit * 4, 20),
                        "language": "ru",
                        "countryCode": "RU",
                        "format": "json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            logger.exception("city geocode failed for %s", q)
            # Transient upstream failures must not be cached as "no cities".
            return [
                city
                for city in POPULAR_CITIES
                if q.casefold() in city["name"].casefold()
            ][:limit]

        ranked = sorted(
            (item for item in (payload.get("results") or []) if is_trip_city(item)),
            key=lambda item: int(item.get("population") or 0),
            reverse=True,
        )

        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in ranked:
            if str(item.get("country_code") or "").upper() != "RU":
                continue
            row = _result_row(item)
            if row is None:
                continue
            key = row["name"].casefold()
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows

    return await cached_json(cache_key, keys.TTL_GEONAME, produce)
