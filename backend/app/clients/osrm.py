import asyncio
import math

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ORS_URL = "https://api.openrouteservice.org/v2/directions"
#: ORS profile names differ from OSRM's.
ORS_PROFILES = {"foot": "foot-walking", "driving": "driving-car"}

#: Mirrors the endpoint list the frontend uses in web/src/shared/lib/osrm/route.ts.
ENDPOINTS: dict[str, tuple[str, ...]] = {
    "foot": (
        "https://routing.openstreetmap.de/routed-foot/route/v1/foot",
        "https://router.project-osrm.org/route/v1/foot",
    ),
    "driving": (
        "https://routing.openstreetmap.de/routed-car/route/v1/driving",
        "https://router.project-osrm.org/route/v1/driving",
    ),
}

WALK_SPEED_MPS = 1.25
DRIVE_SPEED_MPS = 8.0


def haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two [lon, lat] points."""
    lon1, lat1 = a
    lon2, lat2 = b
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def estimate(a: tuple[float, float], b: tuple[float, float], profile: str) -> dict[str, float]:
    """Straight-line fallback when OSRM is unreachable."""
    meters = haversine_meters(a, b) * 1.3  # rough detour factor
    speed = DRIVE_SPEED_MPS if profile == "driving" else WALK_SPEED_MPS
    return {"distance": meters, "duration": meters / speed}


class OsrmClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(4)
        self._ors_lock = asyncio.Lock()
        self._ors_next_slot = 0.0
        #: Flipped once ORS refuses us (bad key, daily quota gone) so the rest
        #: of the trip does not pay a timeout per leg.
        self._ors_disabled = False
        #: Public OSRM mirrors unreachable from this host (common on locked-down VDS).
        self._osrm_disabled = False

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            # Keep this tight: a blocked upstream must not stall a whole trip.
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0))
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _pace_ors(self) -> None:
        interval = settings.ors_min_interval
        if interval <= 0:
            return
        async with self._ors_lock:
            now = asyncio.get_running_loop().time()
            wait = self._ors_next_slot - now
            self._ors_next_slot = max(now, self._ors_next_slot) + interval
        if wait > 0:
            await asyncio.sleep(wait)

    async def _ors_leg(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str,
    ) -> dict[str, float] | None:
        if self._ors_disabled or not settings.ors_configured:
            return None

        ors_profile = ORS_PROFILES.get(profile)
        if ors_profile is None:
            return None

        await self._pace_ors()
        client = await self._http()
        try:
            async with self._semaphore:
                response = await client.get(
                    f"{ORS_URL}/{ors_profile}",
                    params={
                        "api_key": settings.ors_api_key,
                        "start": f"{origin[0]},{origin[1]}",
                        "end": f"{destination[0]},{destination[1]}",
                    },
                )
        except httpx.HTTPError as exc:
            # Timeouts / unreachable hosts will repeat for every leg otherwise.
            logger.warning("ORS unreachable (%s), using geometric estimates", exc)
            self._ors_disabled = True
            return None

        if response.status_code in {401, 403}:
            # Key rejected or the daily quota is spent — stop trying.
            logger.warning("ORS refused the key (%s), falling back to OSRM", response.status_code)
            self._ors_disabled = True
            return None
        if response.status_code != 200:
            logger.debug("ORS returned %s", response.status_code)
            return None

        features = response.json().get("features") or []
        if not features:
            return None
        summary = (features[0].get("properties") or {}).get("summary") or {}
        distance, duration = summary.get("distance"), summary.get("duration")
        if distance is None or duration is None:
            # ORS omits the summary when both points snap to the same node.
            return None
        return {"distance": float(distance), "duration": float(duration)}

    async def leg(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str = "foot",
    ) -> dict[str, float]:
        """Distance (m) and duration (s) for one hop, with a geometric fallback.

        Tries openrouteservice first, then the public OSRM mirrors, then plain
        geometry — a leg is never allowed to fail the whole trip.
        """
        coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"

        async def produce() -> dict[str, float]:
            from_ors = await self._ors_leg(origin, destination, profile)
            if from_ors is not None:
                return from_ors

            if not self._osrm_disabled:
                client = await self._http()
                for base in ENDPOINTS.get(profile, ENDPOINTS["foot"]):
                    async with self._semaphore:
                        try:
                            response = await client.get(f"{base}/{coords}?overview=false")
                        except httpx.HTTPError as exc:
                            logger.warning("OSRM unreachable (%s), skipping mirrors", exc)
                            self._osrm_disabled = True
                            break

                    if response.status_code != 200:
                        continue
                    routes = response.json().get("routes") or []
                    if not routes:
                        continue
                    return {
                        "distance": float(routes[0].get("distance", 0.0)),
                        "duration": float(routes[0].get("duration", 0.0)),
                    }

            return estimate(origin, destination, profile)

        return await cached_json(keys.osrm(profile, coords), keys.TTL_OSRM, produce)


osrm = OsrmClient()
