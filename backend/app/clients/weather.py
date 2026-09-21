"""Daily forecast from Open-Meteo — free, keyless, no registration.

A trip can be planned months ahead, well past any real forecast. Rather than
invent numbers we return nothing for those days and let the UI say so: a made-up
temperature is worse than an honest "прогноза пока нет".
"""
import asyncio
from datetime import date

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.core.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"

#: Open-Meteo publishes 16 days ahead. Past that there is no forecast to show.
FORECAST_HORIZON_DAYS = 16

#: WMO weather codes collapsed into the few buckets a traveller cares about.
#: (label, icon) — the icon key is what the frontend maps to an illustration.
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Ясно", "clear"),
    1: ("Малооблачно", "clear"),
    2: ("Переменная облачность", "cloudy"),
    3: ("Пасмурно", "cloudy"),
    45: ("Туман", "fog"),
    48: ("Изморозь", "fog"),
    51: ("Морось", "rain"),
    53: ("Морось", "rain"),
    55: ("Морось", "rain"),
    56: ("Ледяная морось", "sleet"),
    57: ("Ледяная морось", "sleet"),
    61: ("Небольшой дождь", "rain"),
    63: ("Дождь", "rain"),
    65: ("Сильный дождь", "rain"),
    66: ("Ледяной дождь", "sleet"),
    67: ("Ледяной дождь", "sleet"),
    71: ("Небольшой снег", "snow"),
    73: ("Снег", "snow"),
    75: ("Сильный снег", "snow"),
    77: ("Снежная крупа", "snow"),
    80: ("Ливень", "rain"),
    81: ("Ливень", "rain"),
    82: ("Сильный ливень", "rain"),
    85: ("Снегопад", "snow"),
    86: ("Сильный снегопад", "snow"),
    95: ("Гроза", "storm"),
    96: ("Гроза с градом", "storm"),
    99: ("Гроза с градом", "storm"),
}


def describe(code: int) -> tuple[str, str]:
    return WMO_CODES.get(code, ("Без осадков", "cloudy"))


def within_horizon(day: date, *, today: date | None = None) -> bool:
    reference = today or date.today()
    return 0 <= (day - reference).days <= FORECAST_HORIZON_DAYS


class WeatherClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(2)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def daily(
        self, *, lat: float, lon: float, start: date, end: date
    ) -> dict[str, dict]:
        """Forecast per ISO date, covering only the days Open-Meteo can answer.

        Days outside the horizon are simply absent from the result — the caller
        renders those as "прогноза пока нет".
        """
        today = date.today()
        first = max(start, today)
        last = min(end, today.fromordinal(today.toordinal() + FORECAST_HORIZON_DAYS))
        if first > last:
            return {}

        first_iso, last_iso = first.isoformat(), last.isoformat()

        async def produce() -> dict[str, dict]:
            client = await self._http()
            params = {
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "start_date": first_iso,
                "end_date": last_iso,
            }
            async with self._semaphore:
                response = await client.get(BASE_URL, params=params)

            if response.status_code != 200:
                logger.warning("Open-Meteo returned %s", response.status_code)
                return {}

            daily = response.json().get("daily") or {}
            times = daily.get("time") or []
            codes = daily.get("weather_code") or []
            highs = daily.get("temperature_2m_max") or []
            lows = daily.get("temperature_2m_min") or []
            rain = daily.get("precipitation_probability_max") or []

            out: dict[str, dict] = {}
            for index, iso in enumerate(times):
                code = int(codes[index]) if index < len(codes) else 0
                label, icon = describe(code)
                high = highs[index] if index < len(highs) else None
                low = lows[index] if index < len(lows) else None
                if high is None or low is None:
                    continue
                out[iso] = {
                    "label": label,
                    "icon": icon,
                    "tempHigh": round(float(high)),
                    "tempLow": round(float(low)),
                    "precipitationChance": (
                        int(rain[index]) if index < len(rain) and rain[index] is not None else None
                    ),
                }
            return out

        try:
            return await cached_json(
                keys.weather(lat, lon, first_iso, last_iso), keys.TTL_WEATHER, produce
            )
        except Exception as exc:  # noqa: BLE001 - weather is a garnish, never a blocker
            logger.warning("Weather lookup failed: %s", exc)
            return {}


weather = WeatherClient()
