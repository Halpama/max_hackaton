"""Split selected places into days and assign concrete times."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.clients.osrm import haversine_meters
from app.schemas.trip import TripPace
from app.services.places import PlaceCandidate

#: Activities per day by pace.
PACE_ACTIVITY_COUNT: dict[TripPace, int] = {"calm": 3, "medium": 5, "active": 7}

#: Minutes spent at a place, by category.
VISIT_MINUTES: dict[str, int] = {
    "museum": 120,
    "location": 45,
    "food": 60,
    "walk": 120,
}

#: Ceiling when a thin day has spare hours to fill (only stretchable stops).
STAY_CAP_MINUTES: dict[str, int] = {
    "museum": 180,
    "location": 60,
    "food": 75,
    "walk": 270,
}

#: Floor for a solo day-trip worth lingering (never for photo-stops).
SOLO_MIN_STAY: dict[str, int] = {
    "museum": 150,
    "location": 45,
    "food": 60,
    "walk": 210,
}

#: Stops shorter than this are photo/look points — do not pad them to fill a day.
SHORT_STOP_MINUTES = 45

#: A calm trip lingers, an active one moves on quickly.
PACE_DURATION_FACTOR: dict[TripPace, float] = {"calm": 1.25, "medium": 1.0, "active": 0.8}

#: Two meals a day is plenty; more turns an itinerary into a food crawl.
MAX_MEALS_PER_DAY = 2

#: Hard ceiling for a same-day hop. Beyond this a place belongs on another day
#: (Sviyazhsk ↔ Kazan is ~60 km — never share a day with a city café).
MAX_SAME_DAY_METERS = 18_000

DEFAULT_DAY_START = time(9, 30)
DEFAULT_DAY_END = time(21, 0)
#: Below this a day is not worth scheduling (late arrival / early departure).
MIN_USABLE_DAY_MINUTES = 90


@dataclass
class DaySlot:
    index: int
    day: date
    start: datetime
    end: datetime

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def _snap_quarter(minutes: float) -> int:
    return max(30, int(round(minutes / 15) * 15))


def visit_minutes(candidate: PlaceCandidate, pace: TripPace) -> int:
    # GigaChat estimate wins when present — pace already baked into the prompt.
    if candidate.stay_minutes is not None:
        return _snap_quarter(candidate.stay_minutes)
    base = VISIT_MINUTES.get(candidate.category_kind, 60)
    return _snap_quarter(base * PACE_DURATION_FACTOR.get(pace, 1.0))


def _is_stretchable(candidate: PlaceCandidate, base: int) -> bool:
    """Fountains and statues must not absorb leftover afternoon hours."""
    if base <= SHORT_STOP_MINUTES:
        return False
    if candidate.category_kind == "food":
        return False
    if candidate.category_kind == "location":
        return False
    return candidate.category_kind in {"museum", "walk"}


def allocate_stays(
    day: list[PlaceCandidate],
    pace: TripPace,
    slot_minutes: int,
    transit_minutes: list[int] | None = None,
) -> list[int]:
    """Stretch only lingering stops when a day would otherwise look half-empty.

    A lone island walk reads as a half-day trip; a fountain stays a short look.
    """
    if not day:
        return []

    stays = [visit_minutes(c, pace) for c in day]
    transit = list(transit_minutes or [])
    transit_total = sum(transit[: max(0, len(day) - 1)])

    if len(day) == 1:
        kind = day[0].category_kind
        if not _is_stretchable(day[0], stays[0]):
            return stays
        floor = SOLO_MIN_STAY.get(kind, 150)
        ceiling = min(STAY_CAP_MINUTES.get(kind, 180), max(30, slot_minutes - 60))
        stays[0] = _snap_quarter(min(max(stays[0], floor), ceiling))
        return stays

    spare = slot_minutes - sum(stays) - transit_total
    if spare < 45:
        return stays

    stretchable = [
        i for i, (c, base) in enumerate(zip(day, stays, strict=True)) if _is_stretchable(c, base)
    ]
    if not stretchable:
        return stays

    while spare >= 15:
        grew = False
        for index in stretchable:
            kind = day[index].category_kind
            cap = STAY_CAP_MINUTES.get(kind, 150)
            if stays[index] + 15 > cap:
                continue
            stays[index] += 15
            spare -= 15
            grew = True
            if spare < 15:
                break
        if not grew:
            break

    return stays


def estimate_travel_minutes(
    origin: tuple[float, float], destination: tuple[float, float]
) -> int:
    """Cheap stand-in for OSRM while we are still packing the day."""
    meters = haversine_meters(origin, destination)
    if meters <= 1_300:
        return max(5, int(meters / 80))
    # ~35–40 km/h effective average including waits.
    return max(12, int(meters / 1_000 * 2.0))


def build_day_slots(start: datetime, end: datetime) -> list[DaySlot]:
    """One slot per calendar day, clipped by the arrival and departure times."""
    slots: list[DaySlot] = []
    current = start.date()
    last = end.date()
    index = 0

    while current <= last:
        day_start = start if current == start.date() else datetime.combine(current, DEFAULT_DAY_START)
        day_end = end if current == last else datetime.combine(current, DEFAULT_DAY_END)

        if day_end > day_start:
            usable = int((day_end - day_start).total_seconds() // 60)
            if usable >= MIN_USABLE_DAY_MINUTES:
                slots.append(DaySlot(index=index, day=current, start=day_start, end=day_end))
                index += 1

        current += timedelta(days=1)

    if not slots:
        slots.append(DaySlot(index=0, day=start.date(), start=start, end=start + timedelta(hours=6)))

    return slots


def spread_meals(candidates: list[PlaceCandidate]) -> list[PlaceCandidate]:
    """Space food stops evenly through the list."""
    meals = [c for c in candidates if c.category_kind == "food"]
    rest = [c for c in candidates if c.category_kind != "food"]
    if not meals or not rest:
        return list(candidates)

    ordered = list(rest)
    for index, meal in enumerate(meals):
        position = round((index + 1) * len(rest) / (len(meals) + 1)) + index
        ordered.insert(min(position, len(ordered)), meal)

    return ordered


def _day_centroid(day: list[PlaceCandidate]) -> tuple[float, float]:
    lon = sum(c.coordinates[0] for c in day) / len(day)
    lat = sum(c.coordinates[1] for c in day) / len(day)
    return (lon, lat)


def _fits_day(candidate: PlaceCandidate, day: list[PlaceCandidate]) -> bool:
    """Reject places that would force an absurd same-day taxi."""
    if not day:
        return True
    centroid = _day_centroid(day)
    if haversine_meters(centroid, candidate.coordinates) > MAX_SAME_DAY_METERS:
        return False
    nearest = min(haversine_meters(candidate.coordinates, c.coordinates) for c in day)
    return nearest <= MAX_SAME_DAY_METERS


def _spent_minutes(day: list[PlaceCandidate], pace: TripPace) -> int:
    if not day:
        return 0
    total = visit_minutes(day[0], pace)
    for prev, nxt in zip(day, day[1:], strict=False):
        total += estimate_travel_minutes(prev.coordinates, nxt.coordinates)
        total += visit_minutes(nxt, pace)
    return total


def order_by_proximity(candidates: list[PlaceCandidate]) -> list[PlaceCandidate]:
    """Greedy nearest-neighbour from the densest seed; far leftovers stay last."""
    if len(candidates) <= 1:
        return list(candidates)

    remaining = list(candidates)
    seed = max(
        remaining,
        key=lambda c: sum(
            1
            for other in remaining
            if other is not c
            and haversine_meters(c.coordinates, other.coordinates)
            <= MAX_SAME_DAY_METERS / 2
        ),
    )
    remaining.remove(seed)
    ordered = [seed]

    while remaining:
        current = ordered[-1].coordinates
        in_range = [
            c
            for c in remaining
            if haversine_meters(current, c.coordinates) <= MAX_SAME_DAY_METERS
        ]
        pick_from = in_range or remaining
        nearest = min(pick_from, key=lambda c: haversine_meters(current, c.coordinates))
        remaining.remove(nearest)
        ordered.append(nearest)

    return ordered


def _targets_by_available_time(total: int, slots: list[DaySlot], cap: int) -> list[int]:
    """Split `total` places across days in proportion to each day's free hours."""
    minutes = [max(1, slot.minutes) for slot in slots]
    overall = sum(minutes)

    targets = [min(cap, int(total * part / overall)) for part in minutes]

    while sum(targets) < total:
        room = [
            (minutes[i] / (targets[i] + 1), i)
            for i in range(len(slots))
            if targets[i] < cap
        ]
        if not room:
            break
        targets[max(room)[1]] += 1

    return targets


def distribute(
    candidates: list[PlaceCandidate], slots: list[DaySlot], pace: TripPace
) -> list[list[PlaceCandidate]]:
    """Deal places into days, respecting pace, time and geography.

    A city café never shares a day with a remote suburb: same-day hops are
    capped so itineraries do not bounce 70 minutes each way for a short visit.
    """
    if not slots:
        return []

    cap = PACE_ACTIVITY_COUNT.get(pace, 5)
    shareable = min(len(candidates), cap * len(slots))
    targets = _targets_by_available_time(shareable, slots, cap)

    pool = spread_meals(candidates)
    days: list[list[PlaceCandidate]] = [[] for _ in slots]

    for day_index, (target, slot) in enumerate(zip(targets, slots, strict=True)):
        chosen = days[day_index]
        meals = 0

        for candidate in list(pool):
            if len(chosen) >= target:
                break
            is_meal = candidate.category_kind == "food"
            if is_meal and meals >= MAX_MEALS_PER_DAY:
                continue
            if not _fits_day(candidate, chosen):
                continue

            trial = chosen + [candidate]
            if _spent_minutes(trial, pace) > slot.minutes:
                continue

            chosen.append(candidate)
            pool.remove(candidate)
            meals += is_meal

    # Top up leftovers into the emptiest day that still fits geographically.
    progress = True
    while pool and progress:
        progress = False
        for index in sorted(range(len(days)), key=lambda i: len(days[i])):
            if len(days[index]) >= cap:
                continue
            meals = sum(1 for c in days[index] if c.category_kind == "food")
            for candidate in list(pool):
                if candidate.category_kind == "food" and meals >= MAX_MEALS_PER_DAY:
                    continue
                if not _fits_day(candidate, days[index]):
                    continue
                trial = days[index] + [candidate]
                if _spent_minutes(trial, pace) > slots[index].minutes:
                    continue
                days[index].append(candidate)
                pool.remove(candidate)
                progress = True
                break
            if progress:
                break

    # Remote leftovers: give each its own underfilled day rather than glue it
    # onto a city cluster.
    for candidate in list(pool):
        for index in sorted(range(len(days)), key=lambda i: len(days[i])):
            if days[index]:
                continue
            if visit_minutes(candidate, pace) > slots[index].minutes:
                continue
            days[index].append(candidate)
            pool.remove(candidate)
            break

    return [
        _center_meals(order_by_proximity(day)) if day else day for day in days
    ]


def _center_meals(day: list[PlaceCandidate]) -> list[PlaceCandidate]:
    if len(day) < 3:
        return day

    meals = [c for c in day if c.category_kind == "food"]
    others = [c for c in day if c.category_kind != "food"]
    if not meals or not others:
        return day

    # Only keep meals that still sit near the day's non-food stops.
    near_meals = [m for m in meals if _fits_day(m, others)]
    if not near_meals:
        return others

    middle = len(others) // 2
    return others[:middle] + near_meals[:1] + others[middle:] + near_meals[1:]
