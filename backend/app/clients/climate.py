"""Monthly climate normals via Open-Meteo archive → tourist comfort scores.

Free, keyless. We average a few recent years of daily temperature / precip
into 12 months and map that onto a 1–5 «приятность для прогулок» scale.
Not crowd seasonality — weather comfort — but grounded in real data for any
city coordinates, unlike hand-tuned profiles.
"""

from __future__ import annotations

from collections import defaultdict

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.core.logging import get_logger

logger = get_logger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
#: Recent complete years — enough for a stable monthly mean, small payload.
_CLIMATE_START = "2019-01-01"
_CLIMATE_END = "2023-12-31"
TTL_CLIMATE = 90 * keys.DAY


def comfort_raw(temp_c: float, precip_mm: float) -> float:
    """0..1 comfort for city sightseeing (not ski / beach extremes)."""
    if temp_c <= -15:
        temp_score = 0.05
    elif temp_c <= 0:
        temp_score = 0.15 + (temp_c + 15) / 15 * 0.25
    elif temp_c <= 12:
        temp_score = 0.4 + (temp_c - 0) / 12 * 0.35
    elif temp_c <= 24:
        temp_score = 0.75 + (temp_c - 12) / 12 * 0.25
    elif temp_c <= 30:
        temp_score = 1.0 - (temp_c - 24) / 6 * 0.35
    else:
        temp_score = max(0.25, 0.65 - (temp_c - 30) / 10 * 0.4)

    # Monthly precip: <40mm light, >120mm wet.
    precip_score = 1.0 - min(1.0, max(0.0, precip_mm - 35.0) / 140.0)
    return 0.72 * temp_score + 0.28 * precip_score


def scores_from_monthly(
    months: list[dict[str, float]],
) -> list[int]:
    """Map 12 monthly {temp, precip} dicts onto integers 1..5."""
    if len(months) != 12:
        return []
    raw = [comfort_raw(m["temp"], m["precip"]) for m in months]
    lo, hi = min(raw), max(raw)
    span = hi - lo
    out: list[int] = []
    for value in raw:
        if span < 1e-6:
            score = 3
        else:
            # Keep contrast: coldest month ≠ empty bar.
            norm = (value - lo) / span
            score = int(round(1 + norm * 4))
        out.append(max(1, min(5, score)))
    return out


async def fetch_monthly_climate(lat: float, lon: float) -> list[dict[str, float]]:
    """Return 12 months of mean temp (°C) and precip sum (mm)."""
    cache_key = f"climate:monthly:v1:{round(lat, 2)}:{round(lon, 2)}"

    async def produce() -> list[dict[str, float]]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    ARCHIVE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "start_date": _CLIMATE_START,
                        "end_date": _CLIMATE_END,
                        "daily": "temperature_2m_mean,precipitation_sum",
                        "timezone": "auto",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Open-Meteo climate failed for %s,%s: %s", lat, lon, exc)
            return []

        daily = payload.get("daily") or {}
        times = daily.get("time") or []
        temps = daily.get("temperature_2m_mean") or []
        precips = daily.get("precipitation_sum") or []
        if not times or len(times) != len(temps):
            return []

        buckets: dict[int, dict[str, list[float]]] = defaultdict(
            lambda: {"temps": [], "precips": []}
        )
        for index, day in enumerate(times):
            try:
                month = int(str(day)[5:7])
            except (TypeError, ValueError):
                continue
            temp = temps[index]
            if temp is None:
                continue
            buckets[month]["temps"].append(float(temp))
            precip = precips[index] if index < len(precips) else None
            if precip is not None:
                buckets[month]["precips"].append(float(precip))

        months: list[dict[str, float]] = []
        for month in range(1, 13):
            bucket = buckets.get(month)
            if not bucket or not bucket["temps"]:
                return []
            mean_temp = sum(bucket["temps"]) / len(bucket["temps"])
            # Daily precip → monthly total ≈ mean daily * days in sample / years
            # Approximate: sum all daily precip in month across years / n_years
            years = max(1, len(bucket["temps"]) / 28)
            month_precip = (
                sum(bucket["precips"]) / years if bucket["precips"] else 40.0
            )
            months.append({"temp": mean_temp, "precip": month_precip})
        return months

    return await cached_json(cache_key, TTL_CLIMATE, produce)


async def seasonality_scores(lat: float, lon: float) -> list[int] | None:
    months = await fetch_monthly_climate(lat, lon)
    if not months:
        return None
    scores = scores_from_monthly(months)
    return scores or None
