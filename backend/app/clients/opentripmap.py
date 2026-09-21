import asyncio

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.cache.quota import consume_opentripmap_call
from app.core.config import settings
from app.core.errors import ConfigurationError, NotFoundError, UpstreamError
from app.core.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.opentripmap.com/0.1"

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class OpenTripMapClient:
    """OpenTripMap wrapper. Every network call is cached and quota-counted."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        # The free tier throttles aggressively; keep concurrency low.
        self._semaphore = asyncio.Semaphore(3)
        self._pace_lock = asyncio.Lock()
        self._next_slot = 0.0
        #: Host cannot reach api.opentripmap.com — fail fast for the rest of the trip.
        self._unreachable = False

    async def _pace(self) -> None:
        """Space requests out — bursts of detail lookups earn a 429 otherwise."""
        interval = settings.opentripmap_min_interval
        if interval <= 0:
            return

        async with self._pace_lock:
            now = asyncio.get_running_loop().time()
            wait = self._next_slot - now
            self._next_slot = max(now, self._next_slot) + interval
        if wait > 0:
            await asyncio.sleep(wait)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{BASE_URL}/{settings.opentripmap_lang}/places",
                timeout=httpx.Timeout(5.0, connect=2.5),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict[str, object]) -> object:
        if not settings.opentripmap_configured:
            raise ConfigurationError("OPENTRIPMAP_API_KEY is not set")
        if self._unreachable:
            raise UpstreamError(f"OpenTripMap {path} unavailable: host unreachable")

        client = await self._http()
        query = {**params, "apikey": settings.opentripmap_api_key}

        last_error: str = ""
        for attempt in range(2):
            await consume_opentripmap_call()
            await self._pace()
            async with self._semaphore:
                try:
                    response = await client.get(path, params=query)
                except httpx.TransportError as exc:
                    # Connect/timeouts will not heal mid-trip on this VDS.
                    last_error = str(exc)
                    self._unreachable = True
                    raise UpstreamError(f"OpenTripMap {path} unavailable: {last_error}") from exc
                except httpx.HTTPError as exc:
                    last_error = str(exc)
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue

            if response.status_code == 404:
                raise NotFoundError(f"OpenTripMap: nothing found at {path}")
            if response.status_code in _RETRY_STATUSES:
                last_error = f"{response.status_code} {response.text[:120]}"
                retry_after = response.headers.get("Retry-After")
                backoff = float(retry_after) if (retry_after or "").isdigit() else 0.0
                await asyncio.sleep(max(backoff, 0.5 * (attempt + 1)))
                continue
            if response.status_code != 200:
                raise UpstreamError(
                    f"OpenTripMap {path} failed: {response.status_code} {response.text[:200]}"
                )
            return response.json()

        raise UpstreamError(f"OpenTripMap {path} unavailable: {last_error}")

    async def geoname(self, name: str) -> dict:
        """Resolve a city name to coordinates."""

        async def produce() -> dict:
            data = await self._get("/geoname", {"name": name})
            if not isinstance(data, dict) or "lat" not in data:
                raise NotFoundError(f"City not found: {name}")
            return data

        return await cached_json(keys.geoname(name), keys.TTL_GEONAME, produce)

    async def radius(
        self,
        *,
        lat: float,
        lon: float,
        kinds: str,
        meters: int = 6000,
        rate: int = 2,
        limit: int = 40,
    ) -> list[dict]:
        """List places of the given kinds around a point, best-rated first."""

        async def produce() -> list[dict]:
            data = await self._get(
                "/radius",
                {
                    "radius": meters,
                    "lon": lon,
                    "lat": lat,
                    "kinds": kinds,
                    "rate": rate,
                    "format": "json",
                    "limit": limit,
                },
            )
            return data if isinstance(data, list) else []

        return await cached_json(
            keys.radius(lat, lon, kinds, meters, rate, limit),
            keys.TTL_RADIUS,
            produce,
        )

    async def details(self, xid: str) -> dict:
        """Fetch the full record for one place (description, image, address)."""

        async def produce() -> dict:
            data = await self._get(f"/xid/{xid}", {})
            return data if isinstance(data, dict) else {}

        return await cached_json(keys.xid(xid), keys.TTL_XID, produce)

    async def details_many(self, xids: list[str]) -> dict[str, dict]:
        """Fetch several places concurrently, skipping the ones that fail."""
        results = await asyncio.gather(
            *(self.details(xid) for xid in xids), return_exceptions=True
        )
        out: dict[str, dict] = {}
        for xid, result in zip(xids, results, strict=True):
            if isinstance(result, dict) and result:
                out[xid] = result
            elif isinstance(result, Exception):
                logger.warning("OpenTripMap details failed for %s: %s", xid, result)
        return out


opentripmap = OpenTripMapClient()
