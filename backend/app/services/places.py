"""Turn OpenTripMap and KudaGo records into the Place shape the frontend expects."""
import asyncio
import html
import re
from dataclasses import dataclass, field

from app.clients import kudago as kudago_client
from app.clients.kudago import kudago
from app.clients.opentripmap import opentripmap
from app.clients.osrm import haversine_meters
from app.core.config import settings
from app.core.errors import UpstreamError
from app.core.logging import get_logger
from app.schemas.trip import CategoryKind, RatingSource
from app.services.environment import classify_environment

logger = get_logger(__name__)

#: Interest id (frontend) -> (preferred OpenTripMap kinds, safe fallback).
#: The fallback is used when the provider rejects a narrow kinds combination.
INTEREST_KINDS: dict[str, tuple[str, str]] = {
    "sights": ("interesting_places,architecture,monuments_and_memorials", "interesting_places"),
    "museums": ("museums,theatres_and_entertainments", "museums"),
    "gastro": ("foods", "foods"),
    "walks": ("urban_environment,gardens_and_parks,bridges", "urban_environment"),
    "nature": ("natural,gardens_and_parks", "natural"),
    "unusual": ("other,sculptures,view_points", "interesting_places"),
}

#: Ordered so the most specific label wins.
KIND_LABELS: tuple[tuple[str, str], ...] = (
    ("museums", "Музей"),
    ("theatres_and_entertainments", "Театр и развлечения"),
    ("foods", "Гастрономия"),
    ("gardens_and_parks", "Парк"),
    ("beaches", "Пляж"),
    ("natural", "Природа"),
    ("view_points", "Смотровая площадка"),
    ("fortifications", "Крепость"),
    ("bridges", "Мост"),
    ("sculptures", "Скульптура"),
    ("monuments_and_memorials", "Памятник"),
    ("religion", "Храм"),
    ("historic_architecture", "Историческая архитектура"),
    ("architecture", "Архитектура"),
    ("urban_environment", "Городская среда"),
    ("historic", "Историческое место"),
    ("cultural", "Культура"),
    ("other", "Необычное место"),
    ("interesting_places", "Достопримечательность"),
)

#: Ticketed indoor venues. "cultural" is deliberately absent — OpenTripMap tags
#: open squares and parks with it, which used to price them like a museum.
#: Never offered as a stop. Hotels carry a "foods" tag for their restaurant, so
#: «мини отель пражскии клуб» was turning up as lunch; finding a place to sleep
#: is a separate feature.
EXCLUDED_KINDS = {
    "accomodations",
    "other_hotels",
    "hostels",
    "motels",
    "apartments",
    "guest_houses",
    "campsites",
}

MUSEUM_KINDS = {
    "museums",
    "theatres_and_entertainments",
    "art_galleries",
    "opera_houses",
    "concert_halls",
    "planetariums",
}
FOOD_KINDS = {"foods", "restaurants", "cafes", "bakeries", "pubs"}
WALK_KINDS = {
    "gardens_and_parks",
    "natural",
    "urban_environment",
    "beaches",
    "bridges",
    "squares",
}


@dataclass
class PlaceCandidate:
    """A place we may put into the itinerary, before scheduling and pricing."""

    xid: str
    title: str
    coordinates: tuple[float, float]
    kinds: list[str]
    rate: int
    category: str
    category_kind: CategoryKind
    address: str
    description: str
    image_url: str
    city: str
    interests: set[str] = field(default_factory=set)
    #: Set when a catalogue gives us a real popularity signal. Everything below
    #: falls back to the OpenTripMap projection and is labelled an estimate.
    catalog_rating: float | None = None
    catalog_reviews_label: str | None = None
    opening_hours: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    #: Typical visit length from GigaChat; None → scheduler heuristics.
    stay_minutes: int | None = None
    environment_kind: str = "unknown"

    @property
    def rating(self) -> float:
        if self.catalog_rating is not None:
            return self.catalog_rating
        # OpenTripMap popularity (1..7) projected onto the 5-star UI scale.
        return round(min(5.0, 3.6 + max(self.rate, 1) * 0.2), 1)

    @property
    def rating_source(self) -> RatingSource:
        return "catalog" if self.catalog_rating is not None else "estimate"

    @property
    def reviews_label(self) -> str:
        if self.catalog_reviews_label is not None:
            return self.catalog_reviews_label
        return "оценка по каталогу"


def parse_rate(value: object) -> int:
    """OpenTripMap popularity is 1..7, but heritage objects come back as "3h".

    The `h` suffix marks a listed cultural heritage site, so it earns a point.
    """
    match = re.fullmatch(r"\s*(\d+)\s*(h?)\s*", str(value or ""), flags=re.IGNORECASE)
    if match is None:
        return 0
    return min(7, int(match.group(1)) + bool(match.group(2)))


#: Outdoor memorials whose names leave no doubt. OpenTripMap files them under
#: "museums" as well, which used to sell a ticket for a statue on a square.
MONUMENT_PREFIXES = (
    "памятник",
    "монумент",
    "бюст",
    "обелиск",
    "стела",
    "мемориал",
    "могила",
    "надгробие",
    "скульптура",
    "статуя",
)

SCULPTURE_KINDS = frozenset(
    {
        "sculptures",
        "monuments_and_memorials",
        "monuments",
    }
)


#: Russian place names carry their type as the first or last word — «Конюшенная
#: площадь», «Парк "Дендрарий"». OpenTripMap still files some of them under
#: "museums", which put a ticket price on an open square.
OPEN_AIR_WORDS = frozenset(
    {
        "площадь",
        "сквер",
        "бульвар",
        "набережная",
        "переулок",
        "улица",
        "проспект",
        "аллея",
        "пристань",
        "мост",
        "парк",
        "сад",
        "роща",
        "пляж",
    }
)


def is_outdoor_monument(title: str, kinds: list[str]) -> bool:
    """True for statues / memorials that should not be sold as museum tickets."""
    kind_set = set(kinds) & SCULPTURE_KINDS
    if not kind_set:
        return False
    lowered = title.strip().lower()
    if lowered.startswith(MONUMENT_PREFIXES):
        return True
    # Bare sculpture tags are outdoor art even without «Памятник …» in the name.
    return bool(kind_set & {"sculptures", "monuments"})


def is_open_air(title: str) -> bool:
    words = re.findall(r"\w+", title.lower(), flags=re.UNICODE)
    if not words:
        return False
    return bool({words[0], words[-1]} & OPEN_AIR_WORDS)


def pick_category(kinds: list[str], title: str = "") -> str:
    if "sculptures" in kinds and not title.strip().lower().startswith(
        ("памятник", "монумент", "бюст", "обелиск", "стела", "мемориал")
    ):
        return "Скульптура"
    if is_outdoor_monument(title, kinds):
        return "Памятник"

    for token, label in KIND_LABELS:
        if token not in kinds:
            continue
        if label == "Музей" and is_open_air(title):
            continue
        return label

    return "Городская среда" if is_open_air(title) else "Достопримечательность"


def pick_category_kind(kinds: list[str], title: str = "") -> CategoryKind:
    kind_set = set(kinds)
    if kind_set & FOOD_KINDS:
        return "food"
    # Real museums keep the museum icon even when also tagged as memorials.
    if kind_set & MUSEUM_KINDS and not is_open_air(title) and not is_outdoor_monument(
        title, kinds
    ):
        return "museum"
    # Sculptures / monuments → statue icon, never walk footprints.
    if kind_set & SCULPTURE_KINDS:
        return "location"
    if kind_set & WALK_KINDS or is_open_air(title):
        return "walk"
    return "location"


_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


def _clean_text(value: str) -> str:
    """Plain text for the UI — KudaGo ships HTML with inline styles."""
    text = html.unescape(value or "")
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = re.sub(r"(?i)</p\s*>", " ", text)
    text = _TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def prettify_title(title: str) -> str:
    """Capitalise the first letter — catalogues often ship «центр семьи "Казан"»."""
    cleaned = _clean_text(title)
    if not cleaned:
        return cleaned
    for index, char in enumerate(cleaned):
        if char.isalpha():
            if char.islower():
                return cleaned[:index] + char.upper() + cleaned[index + 1 :]
            return cleaned
    return cleaned


def build_address(details: dict, city: str) -> str:
    address = details.get("address") or {}
    if not isinstance(address, dict):
        return city

    road = address.get("road") or address.get("pedestrian") or address.get("footway")
    house = address.get("house_number")
    parts = [part for part in (road, house) if part]
    if parts:
        return " ".join(str(part) for part in parts)

    return (
        address.get("suburb")
        or address.get("city_district")
        or address.get("city")
        or address.get("town")
        or city
    )


def _clip_description(text: str, *, limit: int = 2_500) -> str:
    """Keep descriptions readable without chopping mid-word like `text[:600]`."""
    text = text.strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    for sep in (". ", "! ", "? ", "… "):
        idx = window.rfind(sep)
        if idx >= limit // 2:
            return window[: idx + 1].strip()
    idx = window.rfind(" ")
    if idx >= limit // 2:
        return window[:idx].rstrip(".,;:") + "…"
    return window.rstrip() + "…"


def build_description(details: dict, fallback_category: str, city: str) -> str:
    extracts = details.get("wikipedia_extracts") or {}
    if isinstance(extracts, dict):
        text = _clean_text(extracts.get("text", ""))
        if len(text) > 40:
            return _clip_description(text)

    info = details.get("info") or {}
    if isinstance(info, dict):
        text = _clean_text(info.get("descr", ""))
        if len(text) > 40:
            return _clip_description(text)

    return f"{fallback_category} в городе {city}. Подробное описание пока недоступно."


def build_image_url(details: dict) -> str:
    preview = details.get("preview") or {}
    if isinstance(preview, dict) and preview.get("source"):
        return str(preview["source"])
    if details.get("image"):
        return str(details["image"])
    return ""


def to_candidate(details: dict, city: str, interests: set[str]) -> PlaceCandidate | None:
    """Build a candidate from an OpenTripMap `xid` payload, or None if unusable."""
    xid = details.get("xid")
    name = prettify_title(details.get("name", ""))
    point = details.get("point") or {}

    if not xid or not name or "lon" not in point or "lat" not in point:
        return None

    kinds = [k for k in str(details.get("kinds", "")).split(",") if k]
    if set(kinds) & EXCLUDED_KINDS:
        return None
    category = pick_category(kinds, name)
    category_kind = pick_category_kind(kinds, name)
    description = build_description(details, category, city)

    return PlaceCandidate(
        xid=str(xid),
        title=name,
        coordinates=(float(point["lon"]), float(point["lat"])),
        kinds=kinds,
        rate=max(1, parse_rate(details.get("rate"))),
        category=category,
        category_kind=pick_category_kind(kinds, name),
        address=build_address(details, city),
        description=build_description(details, category, city),
        image_url=build_image_url(details),
        city=city,
        interests=set(interests),
    )


#: KudaGo category slug -> (label, CategoryKind). Ordered most specific first.
KUDAGO_CATEGORY_MAP: tuple[tuple[str, str, CategoryKind], ...] = (
    ("restaurants", "Гастрономия", "food"),
    ("bar", "Бар", "food"),
    ("anticafe", "Антикафе", "food"),
    ("museums", "Музей", "museum"),
    ("theatre", "Театр", "museum"),
    ("concert-hall", "Концертный зал", "museum"),
    ("art-centers", "Арт-центр", "museum"),
    ("art-space", "Арт-пространство", "museum"),
    ("observatory", "Обсерватория", "museum"),
    ("questroom", "Квест", "museum"),
    ("palace", "Дворец", "museum"),
    ("homesteads", "Усадьба", "museum"),
    ("prirodnyj-zapovednik", "Заповедник", "walk"),
    ("park", "Парк", "walk"),
    ("suburb", "Загородный отдых", "walk"),
    ("bridge", "Мост", "location"),
    ("fountain", "Фонтан", "location"),
    ("church", "Храм", "location"),
    ("monastery", "Монастырь", "location"),
    ("temple", "Храм", "location"),
    ("photo-places", "Фотоместо", "location"),
    ("attractions", "Достопримечательность", "location"),
    ("sights", "Интересное место", "location"),
)


def kudago_category(categories: list[str], title: str) -> tuple[str, CategoryKind]:
    present = set(categories)
    for slug, label, kind in KUDAGO_CATEGORY_MAP:
        if slug in present:
            # An open square tagged "museums" must not be sold a ticket.
            if kind == "museum" and is_open_air(title):
                continue
            return label, kind
    return ("Городская среда", "walk") if is_open_air(title) else ("Достопримечательность", "location")


def popularity_rating(rank: int, total: int) -> float:
    """Rank inside the city catalogue, mapped onto the 5-star scale.

    Scoring the raw favourites count against the city leader squeezes everything
    into the top fifth of a star: the Hermitage has thousands of saves, so a fine
    museum with four hundred still scores 4.8 and no place looks different from
    any other. A rank spreads the shortlist out and means something plain — this
    is the Nth best-known place in town.
    """
    if total <= 1:
        return 4.6
    share = 1.0 - min(rank, total - 1) / (total - 1)
    return round(3.9 + 1.1 * share, 1)


def popularity_rate(rank: int, total: int) -> int:
    """The same rank on OpenTripMap's 1..7 scale, which pricing still speaks."""
    if total <= 1:
        return 4
    share = 1.0 - min(rank, total - 1) / (total - 1)
    return max(1, min(7, 1 + round(share * 6)))


def kudago_to_candidate(
    item: dict, city: str, interests: set[str], *, rank: int, total: int
) -> PlaceCandidate | None:
    title = prettify_title(item.get("title") or "")
    coords = item.get("coords") or {}
    lat, lon = coords.get("lat"), coords.get("lon")
    if not title or lat is None or lon is None:
        return None

    categories = [str(c) for c in (item.get("categories") or [])]
    label, kind = kudago_category(categories, title)

    description = _clean_text(item.get("description") or "") or _clean_text(
        item.get("body_text") or ""
    )
    if len(description) < 40:
        description = f"{label} в городе {city}. Подробное описание пока недоступно."

    images = item.get("images") or []
    image_url = ""
    if images:
        first = images[0] or {}
        thumbs = first.get("thumbnails") or {}
        image_url = str(thumbs.get("640x384") or first.get("image") or "")

    favorites = int(item.get("favorites_count") or 0)
    address = _clean_text(item.get("address") or "") or city
    timetable = _clean_text(item.get("timetable") or "") or None

    return PlaceCandidate(
        xid=f"kudago:{item.get('id')}",
        title=title,
        coordinates=(float(lon), float(lat)),
        kinds=categories,
        # Keep a 1..7 shadow so the existing ranking and pricing keep working.
        rate=popularity_rate(rank, total),
        category=label,
        category_kind=kind,
        address=address,
        description=_clip_description(description),
        image_url=image_url,
        city=city,
        interests=set(interests),
        catalog_rating=popularity_rating(rank, total),
        catalog_reviews_label=f"{favorites} в избранном",
        opening_hours=timetable,
        source_url=str(item.get("site_url") or "") or None,
        source_name="KudaGo",
    )


async def collect_kudago(
    *, city: str, interests: list[str], needed: int
) -> list[PlaceCandidate]:
    """Places from the KudaGo catalogue, best-known first.

    Only a dozen cities are covered, so an empty list is the normal outcome
    everywhere else and OpenTripMap carries the trip on its own.
    """
    if not settings.kudago_enabled:
        return []

    slug = kudago_client.city_slug(city)
    if slug is None:
        return []

    items = await kudago.places(location=slug, interests=interests)
    if not items:
        return []

    wanted = set(interests)
    # The catalogue arrives ordered by popularity, so the index is the rank.
    total = len(items)

    candidates: list[PlaceCandidate] = []
    for rank, item in enumerate(items):
        candidate = kudago_to_candidate(item, city, wanted, rank=rank, total=total)
        if candidate is not None:
            candidates.append(candidate)

    logger.info("KudaGo contributed %d candidate(s) for %s", len(candidates), city)
    return dedupe_for_target(candidates, needed)


def merge_sources(
    primary: list[PlaceCandidate], secondary: list[PlaceCandidate], needed: int
) -> list[PlaceCandidate]:
    """Append whatever the fallback source adds that the primary one missed."""
    merged = list(primary)
    for candidate in secondary:
        if len(merged) >= max(needed, len(primary)) + needed:
            break
        title = normalize_title(candidate.title)
        if any(normalize_title(kept.title) == title for kept in merged):
            continue
        if any(is_duplicate(candidate, kept, SAME_KIND_METERS) for kept in merged):
            continue
        merged.append(candidate)
    return merged


#: Anything closer than this is the same stop as far as a tourist is concerned —
#: OpenTripMap maps one landmark as several xids (node, way and relation).
SAME_PLACE_METERS = 120
#: Two stops of the same type this close read as one long stay (the Hermitage
#: wings came back as five separate museums a few metres apart).
SAME_KIND_METERS = 350
#: How many raw hits to pull per interest. One search returns up to ~450 for the
#: price of a single request, and a wide pool is what makes deduplication work.
RAW_SEARCH_LIMIT = 300


def normalize_title(title: str) -> str:
    """Key used to spot repeats — parenthetical qualifiers are dropped.

    The Sochi arboretum arrives as «Парк "Дендрарий" (верхний)» and «(нижний)»,
    which is one park as far as a day plan is concerned.
    """
    without_qualifier = re.sub(r"\([^)]*\)", " ", title)
    return re.sub(r"[^\w]+", " ", without_qualifier.lower(), flags=re.UNICODE).strip()


def is_duplicate(
    candidate: PlaceCandidate, kept: PlaceCandidate, same_kind_meters: int
) -> bool:
    distance = haversine_meters(candidate.coordinates, kept.coordinates)
    if distance <= SAME_PLACE_METERS:
        return True
    return (
        distance <= same_kind_meters
        and candidate.category_kind == kept.category_kind
        and candidate.category_kind != "food"
    )


def dedupe_candidates(
    candidates: list[PlaceCandidate], *, same_kind_meters: int = SAME_KIND_METERS
) -> list[PlaceCandidate]:
    """Collapse repeated and neighbouring entries into one stop each."""
    kept: list[PlaceCandidate] = []
    seen_titles: set[str] = set()

    for candidate in candidates:
        title = normalize_title(candidate.title)
        if not title or title in seen_titles:
            continue
        if any(is_duplicate(candidate, other, same_kind_meters) for other in kept):
            continue
        kept.append(candidate)
        seen_titles.add(title)

    return kept


def dedupe_for_target(
    candidates: list[PlaceCandidate], needed: int
) -> list[PlaceCandidate]:
    """Deduplicate as strictly as the city allows.

    Full strength suits a dense historic centre, where a dozen entries describe
    one palace complex. A smaller town has genuinely few landmarks, and the same
    rule would leave three stops on one street — so relax until there is enough.
    """
    for threshold in (SAME_KIND_METERS, 200, 0):
        kept = dedupe_candidates(candidates, same_kind_meters=threshold)
        if len(kept) >= needed:
            return kept

    return kept


def balance_food(
    selected: list[PlaceCandidate], candidates: list[PlaceCandidate], wanted: int
) -> list[PlaceCandidate]:
    """Aim for roughly one meal per day, swapping places to keep the length.

    Left alone the mix swings both ways: popularity ranking buries cafés under
    famous museums, while a gastro-heavy candidate pool turns the whole trip
    into a food crawl. Either way the itinerary stops looking planned.
    """
    if wanted < 0:
        return selected

    result = list(selected)

    def meals() -> list[PlaceCandidate]:
        return [c for c in result if c.category_kind == "food"]

    def sights() -> list[PlaceCandidate]:
        return [c for c in result if c.category_kind != "food"]

    spare_food = sorted(
        (c for c in candidates if c.category_kind == "food" and c not in result),
        key=lambda c: c.rate,
        reverse=True,
    )
    for candidate in spare_food:
        if len(meals()) >= wanted or not sights():
            break
        result.remove(min(sights(), key=lambda c: c.rate))
        result.append(candidate)

    spare_sights = sorted(
        (c for c in candidates if c.category_kind != "food" and c not in result),
        key=lambda c: c.rate,
        reverse=True,
    )
    for candidate in spare_sights:
        if len(meals()) <= wanted:
            break
        result.remove(min(meals(), key=lambda c: c.rate))
        result.append(candidate)

    # No sights left to swap in — just drop the surplus cafés.
    while len(meals()) > wanted:
        result.remove(min(meals(), key=lambda c: c.rate))

    return result


async def _radius_with_fallback(
    *, lat: float, lon: float, kinds: str, fallback: str, meters: int, limit: int
) -> list[dict]:
    try:
        return await opentripmap.radius(
            lat=lat, lon=lon, kinds=kinds, meters=meters, limit=limit
        )
    except UpstreamError as exc:
        logger.warning("Kinds '%s' rejected (%s), retrying with '%s'", kinds, exc, fallback)
        try:
            return await opentripmap.radius(
                lat=lat, lon=lon, kinds=fallback, meters=meters, limit=limit
            )
        except UpstreamError as retry_exc:
            # Host cannot reach OpenTripMap at all — let KudaGo carry the trip.
            logger.warning("OpenTripMap radius unavailable: %s", retry_exc)
            return []


async def _search_radius(
    *,
    city: str,
    lat: float,
    lon: float,
    interests: list[str],
    needed: int,
    radius_meters: int,
) -> list[PlaceCandidate]:
    """One pass of the search at a fixed radius."""
    active = [i for i in interests if i in INTEREST_KINDS] or ["sights"]
    # Keep a deep shortlist per interest: details calls drop entries without a
    # name or coordinates, and deduplication prunes hard in historic centres.
    # Depth is free here — hydration below is what costs quota, and it stops
    # as soon as the itinerary has enough places.
    per_interest = max(24, (needed * 4) // len(active) + 10)

    async def fetch_interest(interest: str) -> tuple[str, list[dict]]:
        kinds, fallback = INTEREST_KINDS[interest]
        try:
            found = await _radius_with_fallback(
                lat=lat,
                lon=lon,
                kinds=kinds,
                fallback=fallback,
                meters=radius_meters,
                limit=RAW_SEARCH_LIMIT,
            )
        except Exception as exc:  # noqa: BLE001 - one bad interest must not kill the trip
            logger.warning("Radius search failed for %s: %s", interest, exc)
            return interest, []

        usable = [item for item in found if item.get("xid") and _clean_text(item.get("name", ""))]
        usable.sort(key=lambda item: parse_rate(item.get("rate")), reverse=True)

        # Drop same-name repeats here so they never cost us a details call.
        by_name: dict[str, dict] = {}
        for item in usable:
            by_name.setdefault(normalize_title(_clean_text(item["name"])), item)
        return interest, list(by_name.values())[:per_interest]

    # These searches are independent. Keep the original interest order when
    # merging so ranking and selection remain deterministic.
    ranked = dict(await asyncio.gather(*(fetch_interest(interest) for interest in active)))

    # Round-robin the per-interest lists into one ordered xid list.
    xid_to_interests: dict[str, set[str]] = {}
    ordered: list[str] = []
    for position in range(per_interest):
        for interest, items in ranked.items():
            if position >= len(items):
                continue
            xid = str(items[position]["xid"])
            xid_to_interests.setdefault(xid, set()).add(interest)
            if xid not in ordered:
                ordered.append(xid)

    if not ordered:
        return []

    # Hydrate in batches and stop as soon as there is enough: each detail call
    # costs a request from the daily quota.
    candidates: list[PlaceCandidate] = []
    batch = max(needed + 8, 16)

    for start in range(0, len(ordered), batch):
        chunk = ordered[start : start + batch]
        details = await opentripmap.details_many(chunk)

        for xid in chunk:
            payload = details.get(xid)
            if not payload:
                continue
            try:
                candidate = to_candidate(payload, city, xid_to_interests.get(xid, set()))
            except Exception as exc:  # noqa: BLE001 - one odd record must not kill the trip
                logger.warning("Skipping malformed place %s: %s", xid, exc)
                continue
            if candidate is not None:
                candidates.append(candidate)

        # Judge progress by the strict rule: relaxing it here would stop the
        # search on the first, purely central batch and the trip would never
        # leave one square.
        if len(dedupe_candidates(candidates)) >= needed:
            break

    return dedupe_for_target(candidates, needed)


#: OpenTripMap will happily answer for a whole region; past this the "trip"
#: stops being about one city.
MAX_RADIUS_METERS = 25_000


async def collect_candidates(
    *,
    city: str,
    lat: float,
    lon: float,
    interests: list[str],
    needed: int,
    radius_meters: int = 7000,
) -> list[PlaceCandidate]:
    """Search OpenTripMap per interest, then hydrate the best hits with details.

    Results are interleaved across interests so every selected interest is
    represented even when one of them dominates by popularity.

    Smaller cities do not have `needed` distinct landmarks downtown, so the
    search widens until it finds enough rather than returning three stops on
    the same street. Repeat passes are cheap: every call is cached.

    KudaGo goes first where it has coverage — it carries opening hours, real
    popularity and edited Russian copy, none of which OpenTripMap has — and
    OpenTripMap fills the rest in, and everything outside those cities.
    """
    curated = await collect_kudago(city=city, interests=interests, needed=needed)
    if len(curated) >= needed:
        logger.info("KudaGo alone covers %s (%d place(s))", city, len(curated))
        return curated

    best: list[PlaceCandidate] = []

    for multiplier in (1, 2, 3.5):
        attempt = min(int(radius_meters * multiplier), MAX_RADIUS_METERS)
        found = await _search_radius(
            city=city,
            lat=lat,
            lon=lon,
            interests=interests,
            needed=needed,
            radius_meters=attempt,
        )
        if len(found) > len(best):
            best = found
        if len(best) >= needed or attempt >= MAX_RADIUS_METERS:
            break
        logger.info(
            "Only %d place(s) within %d m of %s, widening the search",
            len(best),
            attempt,
            city,
        )

    return merge_sources(curated, best, needed) if curated else best
