import hashlib
from datetime import UTC, datetime

DAY = 86_400

# TTLs tuned so the free tiers of OpenTripMap and GigaChat are not burned on
# repeated identical requests.
TTL_GEONAME = 90 * DAY
TTL_RADIUS = 7 * DAY
TTL_XID = 30 * DAY
TTL_OSRM = 30 * DAY
TTL_COMPLETION = 1 * DAY
TTL_PLAN = 6 * 3600
TTL_CACHE_LOCK = 60
#: KudaGo is an editorial catalogue — opening hours and ratings move slowly.
TTL_KUDAGO = 7 * DAY
#: Long enough to survive a retry storm, short enough that a forecast issued
#: this morning is not served tomorrow evening.
TTL_WEATHER = 3 * 3600


def digest(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def geoname(name: str) -> str:
    return f"otm:geoname:{name.strip().lower()}"


def radius(lat: float, lon: float, kinds: str, meters: int, rate: int, limit: int) -> str:
    return f"otm:radius:{digest(round(lat, 4), round(lon, 4), kinds, meters, rate, limit)}"


def xid(value: str) -> str:
    return f"otm:xid:{value}"


def osrm(profile: str, coords: str) -> str:
    return f"osrm:{profile}:{digest(coords)}"


def kudago_places(location: str, categories: str, page: int) -> str:
    return f"kudago:places:{location}:{digest(categories, page)}"


def kudago_locations() -> str:
    return "kudago:locations"


def weather(lat: float, lon: float, start: str, end: str) -> str:
    return f"weather:{digest(round(lat, 2), round(lon, 2), start, end)}"


def gigachat_token() -> str:
    return "gigachat:token"


def gigachat_completion(model: str, payload: object) -> str:
    return f"gigachat:completion:{digest(model, payload)}"


def trip_plan(payload: object) -> str:
    return f"trip:plan:v2:{digest(payload)}"


def trip_progress_channel(trip_id: object) -> str:
    return f"trip:{trip_id}:progress"


def trip_progress_log(trip_id: object) -> str:
    """Replay buffer so a late SSE subscriber still sees earlier stages."""
    return f"trip:{trip_id}:events"


def otm_quota() -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"otm:quota:{today}"
