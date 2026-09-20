"""Pick a transport mode for each hop between two consecutive places."""
from app.clients.osrm import haversine_meters, osrm
from app.schemas.trip import TransitLeg, TransitMode

#: Straight-line thresholds in metres.
WALKABLE_METERS = 1300
METRO_METERS = 6000

MODE_LABELS: dict[TransitMode, str] = {
    "walk": "Пешком",
    "metro": "Метро",
    "taxi": "Такси",
}


#: Cities where a "Метро" hint is actually actionable. Everywhere else a long
#: hop becomes a taxi — Sochi has no subway, and the itinerary said otherwise.
METRO_CITIES = frozenset(
    {
        "москва",
        "санкт-петербург",
        "петербург",
        "нижний новгород",
        "новосибирск",
        "екатеринбург",
        "самара",
        "казань",
        "омск",
        "челябинск",
        "красноярск",
        "волгоград",
        "минск",
        "киев",
        "харьков",
        "алматы",
        "ташкент",
        "баку",
        "тбилиси",
        "ереван",
    }
)


def has_metro(city: str) -> bool:
    normalized = city.strip().lower().replace("ё", "е")
    return any(name in normalized for name in METRO_CITIES)


def pick_mode(distance_meters: float, *, metro: bool = True) -> TransitMode:
    if distance_meters <= WALKABLE_METERS:
        return "walk"
    if metro and distance_meters <= METRO_METERS:
        return "metro"
    return "taxi"


def profile_for(mode: TransitMode) -> str:
    return "driving" if mode == "taxi" else "foot"


async def build_leg(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    metro: bool = True,
) -> tuple[TransitLeg, int]:
    """Return the transit hint plus its duration in minutes.

    Metro legs add a flat overhead for entering, waiting and exiting the station.
    """
    straight = haversine_meters(origin, destination)
    mode = pick_mode(straight, metro=metro)

    metrics = await osrm.leg(origin, destination, profile_for(mode))
    minutes = max(1, round(metrics["duration"] / 60))

    if mode == "metro":
        # OSRM has no transit profile; approximate the ride and add station time.
        minutes = max(5, round(straight / 1000 * 3) + 7)

    label = f"{MODE_LABELS[mode]} {minutes} мин"
    return TransitLeg(mode=mode, label=label), minutes
