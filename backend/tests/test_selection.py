"""Place selection rules: deduplication, food balance and day distribution.

These cover the logic that turns a raw OpenTripMap dump into something that
reads like a planned trip rather than a list of nearby objects.
"""
from datetime import date, datetime

from app.services.places import (
    PlaceCandidate,
    balance_food,
    dedupe_candidates,
    to_candidate,
)
from app.services.scheduler import _targets_by_available_time, build_day_slots, distribute

#: ~111 m per 0.001° of latitude, which makes the distances below easy to read.
BASE_LAT, BASE_LON = 59.9386, 30.3141


def candidate(
    xid: str,
    title: str,
    *,
    kind: str = "location",
    north_meters: float = 0.0,
    rate: int = 4,
) -> PlaceCandidate:
    return PlaceCandidate(
        xid=xid,
        title=title,
        coordinates=(BASE_LON, BASE_LAT + north_meters / 111_000),
        kinds=[],
        rate=rate,
        category="Достопримечательность",
        category_kind=kind,  # type: ignore[arg-type]
        address="",
        description="",
        image_url="",
        city="Санкт-Петербург",
    )


def test_hotels_are_not_offered_as_restaurants():
    hotel = {
        "xid": "N1",
        "name": "мини отель пражскии клуб",
        "point": {"lon": BASE_LON, "lat": BASE_LAT},
        "kinds": "accomodations,other_hotels,cafes,foods,tourist_facilities",
    }
    restaurant = {**hotel, "xid": "N2", "name": "Татарская усадьба", "kinds": "restaurants,foods"}

    assert to_candidate(hotel, "Казань", {"gastro"}) is None
    assert to_candidate(restaurant, "Казань", {"gastro"}) is not None


def test_same_landmark_under_two_xids_is_kept_once():
    # OpenTripMap maps one object as a node and a relation a few metres apart.
    kept = dedupe_candidates(
        [
            candidate("R1", "Дворцовая площадь"),
            candidate("N2", "Дворцовая площадь", north_meters=30),
        ]
    )
    assert [c.xid for c in kept] == ["R1"]


def test_neighbouring_wings_of_one_complex_collapse():
    kept = dedupe_candidates(
        [
            candidate("A", "Зимний дворец", kind="museum"),
            candidate("B", "Новый Эрмитаж", kind="museum", north_meters=200),
            candidate("C", "Восточное крыло Главного штаба", kind="museum", north_meters=300),
        ]
    )
    assert [c.xid for c in kept] == ["A"]


def test_different_kinds_next_door_both_survive():
    # A café across the road from a museum is a real second stop.
    kept = dedupe_candidates(
        [
            candidate("A", "Эрмитаж", kind="museum"),
            candidate("B", "Кафе Зингеръ", kind="food", north_meters=200),
        ]
    )
    assert len(kept) == 2


def test_relaxing_the_rule_recovers_places_in_a_small_town():
    crowded = [
        candidate(str(i), f"Место {i}", kind="location", north_meters=i * 150)
        for i in range(5)
    ]
    strict = dedupe_candidates(crowded)
    relaxed = dedupe_candidates(crowded, same_kind_meters=0)

    assert len(strict) < len(relaxed) == 5


def test_balance_food_tops_up_a_gastro_trip():
    selected = [candidate(f"m{i}", f"Музей {i}", kind="museum") for i in range(5)]
    pool = selected + [
        candidate("f1", "Кафе", kind="food", rate=6),
        candidate("f2", "Пышечная", kind="food", rate=5),
    ]

    result = balance_food(selected, pool, wanted=2)

    assert sum(1 for c in result if c.category_kind == "food") == 2
    assert len(result) == len(selected), "swaps must keep the itinerary length"


def test_balance_food_trims_a_food_crawl():
    selected = [candidate(f"f{i}", f"Кафе {i}", kind="food", rate=i + 1) for i in range(6)]
    pool = selected + [
        candidate(f"m{i}", f"Музей {i}", kind="museum", rate=6) for i in range(4)
    ]

    result = balance_food(selected, pool, wanted=2)

    assert sum(1 for c in result if c.category_kind == "food") == 2
    # The cafés that survive are the best rated ones.
    assert {c.xid for c in result if c.category_kind == "food"} == {"f4", "f5"}


def test_targets_follow_available_hours():
    # Arrive at 10:00, leave at 18:00 — the last day is much shorter.
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 18, 18, 0))
    targets = _targets_by_available_time(16, slots, cap=7)

    assert sum(targets) == 16
    assert targets[-1] < max(targets), "the departure day must get a lighter load"
    assert all(t <= 7 for t in targets)


def test_distribute_never_front_loads_day_one():
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 17, 18, 0))
    places = [candidate(str(i), f"Место {i}", north_meters=i * 500) for i in range(7)]

    days = distribute(places, slots, "medium")
    counts = [len(day) for day in days]

    assert sum(counts) == 7
    assert max(counts) - min(counts) <= 1, f"Uneven days: {counts}"


def test_distribute_caps_meals_per_day():
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 16, 18, 0))
    places = [candidate(str(i), f"Кафе {i}", kind="food", north_meters=i * 400) for i in range(8)]

    days = distribute(places, slots, "active")

    for day in days:
        meals = sum(1 for c in day if c.category_kind == "food")
        assert meals <= 2, f"{meals} food stops in one day"


def test_distribute_keeps_remote_stops_off_city_days():
    # ~60 km north — Sviyazhsk-scale outlier must not share a day with downtown.
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 17, 18, 0))
    city = [
        candidate("c1", "Кремль", north_meters=0),
        candidate("c2", "Хинкальная", kind="food", north_meters=800),
        candidate("c3", "Музей", kind="museum", north_meters=1_200),
    ]
    remote = candidate("r1", "Свияжск", kind="walk", north_meters=60_000)

    days = distribute(city + [remote], slots, "medium")
    remote_day = next(day for day in days if any(c.xid == "r1" for c in day))
    assert all(c.xid == "r1" or haversine_ok(c, remote) for c in remote_day)
    assert not any(c.xid == "c2" for c in remote_day), "city lunch must not ride along"


def test_solo_day_trip_gets_a_real_visit():
    from app.services.scheduler import allocate_stays

    remote = candidate("r1", "Свияжск", kind="walk", north_meters=60_000)
    # Full day ~11.5h — a 75-minute pit stop would look absurd.
    stays = allocate_stays([remote], "active", slot_minutes=690)

    assert stays == [210], f"expected a half-day walk, got {stays}"


def test_fountain_is_not_padded_to_fill_the_day():
    from dataclasses import replace

    from app.services.scheduler import allocate_stays

    fountain = replace(
        candidate("f1", "Фонтан на озере", kind="location"),
        stay_minutes=30,
    )
    museum = candidate("m1", "Музей", kind="museum", north_meters=800)
    stays = allocate_stays([fountain, museum], "medium", slot_minutes=690)

    assert stays[0] == 30, f"fountain must stay a short look, got {stays[0]}"
    assert stays[1] >= 120, "spare time goes to the museum instead"


def test_clamp_stay_minutes_bounds():
    from app.services.llm import clamp_stay_minutes, _parse_stops

    assert clamp_stay_minutes(7) == 15
    assert clamp_stay_minutes(28) == 30
    assert clamp_stay_minutes(400) == 240
    assert clamp_stay_minutes("nope") is None

    stops = _parse_stops(
        {"stops": [{"id": "a", "minutes": 25}, {"id": "b", "minutes": 100}]}
    )
    assert stops == [("a", 30), ("b", 105)]


def test_visit_is_clipped_to_closing_time():
    from datetime import datetime, time

    from app.services.opening_hours import fit_visit, hours_for_day

    assert hours_for_day("ежедневно 10:00–20:00", date(2026, 9, 25)) == (
        time(10, 0),
        time(20, 0),
    )
    assert hours_for_day("вт–вс 10:00–17:30", date(2026, 9, 25)) == (
        time(10, 0),
        time(17, 30),
    )  # Friday
    assert hours_for_day("вт–вс 10:00–17:30", date(2026, 9, 21)) is None  # Monday

    start, finish, stay = fit_visit(
        datetime(2026, 9, 25, 18, 15),
        165,
        opening_hours="ежедневно 10:00–20:00",
        day_end=datetime(2026, 9, 25, 21, 0),
    )
    assert finish.hour == 20 and finish.minute == 0
    assert stay == 105
    assert start.hour == 18 and start.minute == 15


def haversine_ok(a: PlaceCandidate, b: PlaceCandidate) -> bool:
    from app.clients.osrm import haversine_meters
    from app.services.scheduler import MAX_SAME_DAY_METERS

    return haversine_meters(a.coordinates, b.coordinates) <= MAX_SAME_DAY_METERS
