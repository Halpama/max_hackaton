"""KudaGo catalogue client — free, keyless, and far richer than OpenTripMap.

OpenTripMap is a stale OSM snapshot: no opening hours, no real popularity, and
descriptions that arrive in whatever language the Wikipedia editor used. KudaGo
is an edited Russian catalogue that ships exactly the fields we were inventing.

It only covers a dozen cities, so this is an enrichment layer rather than a
replacement: `places.py` merges what it finds here over the OpenTripMap base.

The licence asks for an indexable link back to the source, which is why
`site_url` travels with every record.
"""
import asyncio

import httpx

from app.cache import keys
from app.cache.decorator import cached_json
from app.core.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://kudago.com/public-api/v1.4"

#: KudaGo slugs for the cities it covers, keyed by the normalised Russian name
#: we get back from the LLM analysis step.
CITY_SLUGS: dict[str, str] = {
    "москва": "msk",
    "санкт-петербург": "spb",
    "петербург": "spb",
    "спб": "spb",
    "новосибирск": "nsk",
    "екатеринбург": "ekb",
    "нижний новгород": "nnv",
    "казань": "kzn",
    "выборг": "vbg",
    "самара": "smr",
    "краснодар": "krd",
    "сочи": "sochi",
    "уфа": "ufa",
    "красноярск": "krasnoyarsk",
}

#: Our interest ids mapped onto KudaGo place categories. Hotels ("inn",
#: "hostels") are a separate category and simply never requested, which is a
#: structural fix for the «мини отель» that used to be served as lunch.
INTEREST_CATEGORIES: dict[str, tuple[str, ...]] = {
    "sights": ("attractions", "sights", "palace", "homesteads", "bridge", "fountain"),
    "museums": ("museums", "theatre", "concert-hall", "art-space", "art-centers"),
    "gastro": ("restaurants", "bar", "anticafe"),
    "walks": ("park", "sights", "bridge", "fountain"),
    "nature": ("park", "prirodnyj-zapovednik", "suburb"),
    "unusual": ("art-space", "questroom", "photo-places", "amusement", "observatory"),
}

PLACE_FIELDS = ",".join(
    (
        "id",
        "title",
        "short_title",
        "slug",
        "address",
        "timetable",
        "phone",
        "description",
        "body_text",
        "coords",
        "subway",
        "favorites_count",
        "comments_count",
        "is_closed",
        "is_stub",
        "categories",
        "site_url",
        "foreign_url",
        "images",
    )
)

PAGE_SIZE = 100
#: Two pages is plenty: even Moscow only has ~440 places across our categories,
#: and they come back ordered by popularity.
MAX_PAGES = 2


def city_slug(city: str) -> str | None:
    return CITY_SLUGS.get(city.strip().lower())


def categories_for(interests: list[str]) -> str:
    wanted: list[str] = []
    for interest in interests or ["sights"]:
        for category in INTEREST_CATEGORIES.get(interest, ()):
            if category not in wanted:
                wanted.append(category)
    if not wanted:
        wanted = list(INTEREST_CATEGORIES["sights"])
    return ",".join(wanted)


class KudaGoClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(4)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=6.0),
                headers={"User-Agent": "TripPlannerMAX/1.0 (+https://2-rist.ru)"},
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _page(self, location: str, categories: str, page: int) -> list[dict]:
        async def produce() -> list[dict]:
            client = await self._http()
            params = {
                "location": location,
                "categories": categories,
                "fields": PLACE_FIELDS,
                "expand": "images",
                "text_format": "text",
                "page_size": PAGE_SIZE,
                "page": page,
                "order_by": "-favorites_count",
            }
            async with self._semaphore:
                response = await client.get(f"{BASE_URL}/places/", params=params)

            if response.status_code == 404:
                # Paginating past the end is a normal stop condition.
                return []
            if response.status_code != 200:
                logger.warning(
                    "KudaGo places %s page %s: %s", location, page, response.status_code
                )
                return []
            return list(response.json().get("results") or [])

        return await cached_json(
            keys.kudago_places(location, categories, page), keys.TTL_KUDAGO, produce
        )

    async def places(self, *, location: str, interests: list[str]) -> list[dict]:
        """Every usable place in one city, best-known first.

        A failure here must never sink a trip: OpenTripMap still carries the
        itinerary, just without the richer fields.
        """
        categories = categories_for(interests)
        collected: list[dict] = []

        for page in range(1, MAX_PAGES + 1):
            try:
                results = await self._page(location, categories, page)
            except Exception as exc:  # noqa: BLE001 - enrichment is best-effort
                logger.warning("KudaGo lookup failed for %s: %s", location, exc)
                break
            if not results:
                break
            collected.extend(results)
            if len(results) < PAGE_SIZE:
                break

        usable = [
            item
            for item in collected
            if not item.get("is_closed")
            and not item.get("is_stub")
            and (item.get("coords") or {}).get("lat") is not None
        ]
        logger.info("KudaGo returned %d usable place(s) for %s", len(usable), location)
        return usable


kudago = KudaGoClient()
