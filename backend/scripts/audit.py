#!/usr/bin/env python
"""Generate real itineraries and assert they make sense.

Where scripts/smoke.py proves the wiring works, this proves the *content* is
sane: no landmark listed twice, no square with a museum ticket price, no day
that runs past the traveller's departure time.

    python scripts/audit.py
    python scripts/audit.py --scenario spb --verbose
"""
import argparse
import asyncio
import json
import math
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"

GREEN, YELLOW, RED, DIM, BOLD, RESET = (
    "\033[32m",
    "\033[33m",
    "\033[31m",
    "\033[2m",
    "\033[1m",
    "\033[0m",
)

#: Categories the user can walk into without a ticket.
FREE_KINDS = {"walk", "location"}
#: Two stops closer than this are the same landmark under different xids.
SAME_PLACE_METERS = 120
#: Straight-line limit the transit service uses for a walking leg.
WALKABLE_METERS = 1300
MAX_MEALS_PER_DAY = 2

SCENARIOS: dict[str, dict] = {
    "spb": {
        "destination": "Санкт-Петербург",
        "days": 3,
        "budget": 45000,
        "travelers": 2,
        "interests": ["sights", "museums", "gastro"],
        "pace": "medium",
    },
    "kazan": {
        "destination": "Казань",
        "days": 2,
        "budget": 20000,
        "travelers": 1,
        "interests": ["sights", "walks"],
        "pace": "calm",
    },
    "moscow": {
        "destination": "Масква",  # deliberate typo: the LLM should normalise it
        "days": 4,
        "budget": 120000,
        "travelers": 3,
        "interests": ["museums", "gastro", "unusual"],
        "pace": "active",
    },
    "sochi": {
        "destination": "Сочи",
        "days": 2,
        "budget": 8000,
        "travelers": 2,
        "interests": ["nature", "walks"],
        "pace": "medium",
    },
    "nn": {
        "destination": "Нижний Новгород",
        "days": 1,
        "budget": 5000,
        "travelers": 1,
        "interests": ["sights"],
        "pace": "active",
    },
}


class Report:
    """Collects findings for one scenario."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def render(self) -> None:
        status = f"{RED}FAIL{RESET}" if self.errors else (
            f"{YELLOW}WARN{RESET}" if self.warnings else f"{GREEN}OK{RESET}"
        )
        print(f"\n{BOLD}[{self.name}]{RESET} {status}")
        for note in self.notes:
            print(f"  {DIM}·{RESET} {note}")
        for warning in self.warnings:
            print(f"  {YELLOW}!{RESET} {warning}")
        for error in self.errors:
            print(f"  {RED}✗{RESET} {error}")


def haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance between two [lon, lat] pairs."""
    radius = 6_371_000.0
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    d_lat = lat2 - lat1
    d_lon = math.radians(b[0] - a[0])
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def normalize_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", title.lower()).strip()


def parse_time(value: str) -> datetime:
    hours, _, minutes = value.partition(":")
    return datetime(2000, 1, 1, int(hours), int(minutes))


def parse_range_end(time_range: str) -> datetime | None:
    parts = re.split(r"\s*[–—-]\s*", time_range)
    if len(parts) != 2:
        return None
    try:
        return parse_time(parts[1])
    except ValueError:
        return None


def usable_hours_per_day(draft: dict, days: int) -> list[float]:
    """Mirror the backend's day windows: arrival and departure clip the edges."""
    default_start, default_end = parse_time("09:30"), parse_time("21:00")
    hours: list[float] = []

    for index in range(days):
        start = parse_time(draft["startTime"]) if index == 0 else default_start
        end = parse_time(draft["endTime"]) if index == days - 1 else default_end
        hours.append(max(0.5, (end - start).total_seconds() / 3600))

    return hours


def build_draft(spec: dict) -> dict:
    start = date.today() + timedelta(days=14)
    end = start + timedelta(days=spec["days"] - 1)
    return {
        "destination": spec["destination"],
        "startDate": start.isoformat(),
        "startTime": "10:00",
        "endDate": end.isoformat(),
        "endTime": "18:00",
        "budget": spec["budget"],
        "travelers": spec["travelers"],
        "interests": spec["interests"],
        "pace": spec["pace"],
        "findHousing": False,
    }


async def generate(client: httpx.AsyncClient, draft: dict) -> tuple[dict | None, str]:
    created = await client.post("/api/v1/trips", json=draft)
    if created.status_code != 202:
        return None, f"POST /trips → {created.status_code} {created.text[:200]}"

    trip_id = created.json()["id"]
    event_name = ""
    stages: list[str] = []

    async with client.stream(
        "GET", f"/api/v1/trips/{trip_id}/stream", timeout=300.0
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event_name = line[7:].strip()
                continue
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            if event_name == "stage" and payload["status"] == "done":
                stages.append(payload["key"])
            elif event_name == "done":
                return payload["route"], trip_id
            elif event_name == "error":
                trip = await client.get(f"/api/v1/trips/{trip_id}")
                detail = trip.json().get("error") or payload.get("message")
                return None, f"generation failed after {stages}: {detail}"

    return None, "stream closed without a result"


def audit_structure(route: dict, report: Report) -> None:
    places = route["places"]
    scheduled: list[str] = []

    for day in route["days"]:
        activities = day["activities"]
        if not activities:
            report.error(f"{day['label']}: no activities")
        if len(day["transits"]) != max(0, len(activities) - 1):
            report.error(
                f"{day['label']}: {len(day['transits'])} transits "
                f"for {len(activities)} activities"
            )
        for activity in activities:
            scheduled.append(activity["placeId"])
            if activity["placeId"] not in places:
                report.error(f"activity {activity['id']} points at an unknown place")

    repeated = [pid for pid, count in Counter(scheduled).items() if count > 1]
    if repeated:
        report.error(f"place scheduled more than once: {repeated}")

    orphans = set(places) - set(scheduled)
    if orphans:
        report.error(f"{len(orphans)} place(s) in the map but on no day")

    for place_id, place in places.items():
        lon, lat = place["coordinates"]
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            report.error(f"{place_id}: impossible coordinates {place['coordinates']}")
        for field in ("title", "category", "address", "description", "priceLabel"):
            if not str(place.get(field) or "").strip():
                report.error(f"{place_id}: empty {field}")


def audit_duplicates(route: dict, report: Report) -> None:
    places = list(route["places"].values())

    titles = Counter(normalize_title(p["title"]) for p in places)
    dupes = [title for title, count in titles.items() if count > 1]
    if dupes:
        report.error(f"duplicate titles in the itinerary: {dupes}")

    too_close: list[str] = []
    for i, first in enumerate(places):
        for second in places[i + 1 :]:
            distance = haversine_meters(first["coordinates"], second["coordinates"])
            if distance < SAME_PLACE_METERS:
                too_close.append(
                    f"{first['title']} ↔ {second['title']} ({distance:.0f} м)"
                )
    if too_close:
        report.error("stops that are effectively the same spot: " + "; ".join(too_close))


def audit_schedule(route: dict, draft: dict, report: Report) -> None:
    places = route["places"]
    departure = parse_time(draft["endTime"])
    last_day_label = route["days"][-1]["label"] if route["days"] else ""

    for day in route["days"]:
        previous_end: datetime | None = None
        for activity in day["activities"]:
            start = parse_time(activity["time"])
            if previous_end is not None and start < previous_end:
                report.error(
                    f"{day['label']}: {activity['title']} starts at {activity['time']} "
                    f"before the previous stop ends at {previous_end:%H:%M}"
                )
            end = parse_range_end(places[activity["placeId"]]["timeRange"])
            if end is None:
                report.error(f"{activity['id']}: unparsable timeRange")
                continue
            if end <= start:
                report.error(f"{activity['id']}: visit ends before it starts")
            previous_end = end

        if previous_end is None:
            continue
        if day["label"] == last_day_label and previous_end > departure:
            report.error(
                f"{day['label']}: last stop ends at {previous_end:%H:%M}, "
                f"after departure at {draft['endTime']}"
            )
        if previous_end > parse_time("23:00"):
            report.error(f"{day['label']}: schedule runs to {previous_end:%H:%M}")


def audit_pricing(route: dict, draft: dict, report: Report) -> None:
    places = route["places"]
    total = 0.0
    paid_values: list[float] = []

    for place_id, place in places.items():
        value = place.get("priceValue")
        kind = place["categoryKind"]
        label = place["priceLabel"]

        if kind in FREE_KINDS and value:
            report.error(
                f"{place['title']} ({place['category']}) is outdoors "
                f"but costs {label}"
            )
        if value:
            total += value
            paid_values.append(value)
        if (value or 0) <= 0 and label != "Бесплатно":
            report.error(f"{place_id}: price label '{label}' with no value")
        if value and value > draft["budget"]:
            report.error(f"{place['title']}: single stop costs more than the trip budget")

    if total > draft["budget"]:
        report.error(f"planned spend {total:.0f} ₽ exceeds budget {draft['budget']} ₽")

    if len(paid_values) >= 3 and len(set(paid_values)) == 1:
        report.warn(
            f"every paid stop costs exactly {paid_values[0]:.0f} ₽ — looks like a placeholder"
        )

    share = total / draft["budget"] * 100 if draft["budget"] else 0
    report.note(f"planned spend {total:.0f} ₽ of {draft['budget']} ₽ ({share:.0f}%)")


#: Hotels carry a "foods" tag in OpenTripMap for their in-house restaurant.
HOTEL_WORDS = ("отель", "гостиниц", "хостел", "апарт", "hotel", "hostel")


def audit_content(route: dict, report: Report) -> None:
    places = list(route["places"].values())
    if not places:
        return

    with_image = sum(1 for p in places if p.get("imageUrl"))
    generic = sum(1 for p in places if "Подробное описание пока недоступно" in p["description"])

    report.note(
        f"{with_image}/{len(places)} with a photo, "
        f"{len(places) - generic}/{len(places)} with a real description"
    )
    if with_image == 0:
        report.error("no place has a photo — the cards will render empty")
    elif with_image < len(places) * 0.4:
        report.warn(f"only {with_image}/{len(places)} places have a photo")
    if generic > len(places) * 0.6:
        report.warn(f"{generic}/{len(places)} places fall back to a generic description")

    for place in places:
        if normalize_title(place["address"]) == normalize_title(place["city"]):
            report.warn(f"{place['title']}: address is just the city name")
        title = place["title"].lower()
        if place["categoryKind"] == "food" and any(w in title for w in HOTEL_WORDS):
            report.error(f"«{place['title']}» is a hotel, served as a meal")


def audit_balance(route: dict, draft: dict, report: Report) -> None:
    places = route["places"]
    days = route["days"]
    counts = [len(day["activities"]) for day in days]

    expected_days = (
        date.fromisoformat(draft["endDate"]) - date.fromisoformat(draft["startDate"])
    ).days + 1
    if len(days) != expected_days:
        report.warn(f"{len(days)} day(s) planned for a {expected_days}-day trip")

    # A short departure day legitimately holds fewer stops, so compare load per
    # available hour rather than raw counts.
    hours = usable_hours_per_day(draft, len(days))
    density = [count / hour for count, hour in zip(counts, hours)]
    if density and min(density) > 0 and max(density) / min(density) > 2.0:
        report.error(
            f"unbalanced days: {counts} activities over "
            f"{[round(h, 1) for h in hours]} available hours"
        )
    if 0 in counts:
        report.error(f"empty day in the itinerary: {counts}")

    for day in days:
        meals = sum(
            1
            for a in day["activities"]
            if places[a["placeId"]]["categoryKind"] == "food"
        )
        if meals > MAX_MEALS_PER_DAY:
            report.error(f"{day['label']}: {meals} food stops")

    if "gastro" in draft["interests"]:
        total_meals = sum(1 for p in places.values() if p["categoryKind"] == "food")
        if total_meals < len(days):
            report.error(
                f"gastro requested but only {total_meals} food stop(s) across {len(days)} day(s)"
            )

    report.note(f"{len(days)} day(s), {counts} activities, {len(places)} places")


#: Checked independently of the backend list on purpose — the audit is meant to
#: be an outside opinion, not a mirror of the implementation.
CITIES_WITH_METRO = (
    "москв",
    "петербург",
    "новгород",
    "новосибирск",
    "екатеринбург",
    "самар",
    "казан",
    "омск",
    "челябинск",
    "красноярск",
    "волгоград",
)


def audit_transit(route: dict, report: Report) -> None:
    city = route["city"].lower()
    has_metro = any(name in city for name in CITIES_WITH_METRO)

    places = route["places"]
    for day in route["days"]:
        activities = day["activities"]
        for index, leg in enumerate(day["transits"]):
            if leg is None:
                continue
            origin = places[activities[index]["placeId"]]["coordinates"]
            destination = places[activities[index + 1]["placeId"]]["coordinates"]
            distance = haversine_meters(origin, destination)

            if leg["mode"] == "walk" and distance > WALKABLE_METERS * 1.1:
                report.error(
                    f"{day['label']}: '{leg['label']}' for a {distance / 1000:.1f} км hop"
                )
            if leg["mode"] == "metro" and not has_metro:
                report.error(f"routed by metro, but {route['city']} has none")
            if not leg.get("label"):
                report.error(f"{day['label']}: transit leg {index} has no label")


def audit_spread(route: dict, report: Report) -> None:
    coords = [p["coordinates"] for p in route["places"].values()]
    if len(coords) < 3:
        return
    spans = [
        haversine_meters(a, b) for i, a in enumerate(coords) for b in coords[i + 1 :]
    ]
    widest = max(spans)
    report.note(f"itinerary spans {widest / 1000:.1f} км")
    if widest < 400:
        report.error(f"every stop is inside a {widest:.0f} м circle — that is one block")
    elif widest < 900:
        report.warn(f"the whole trip fits in {widest / 1000:.1f} км")


def print_itinerary(route: dict) -> None:
    places = route["places"]
    print(f"  {DIM}{route['city']} · {route['dateLabel']} · {route['budgetLabel']}{RESET}")
    for day in route["days"]:
        print(f"  {DIM}{day['label']}{RESET}")
        for index, activity in enumerate(day["activities"]):
            place = places[activity["placeId"]]
            print(
                f"    {DIM}{activity['time']} {activity['title']} — "
                f"{place['category']}, {place['priceLabel']}{RESET}"
            )
            if index < len(day["transits"]) and day["transits"][index]:
                print(f"      {DIM}↓ {day['transits'][index]['label']}{RESET}")


async def run_scenario(
    client: httpx.AsyncClient, name: str, spec: dict, verbose: bool
) -> Report:
    report = Report(name)
    draft = build_draft(spec)

    route, detail = await generate(client, draft)
    if route is None:
        report.error(detail)
        return report

    report.note(
        f"«{spec['destination']}» → «{route['city']}», "
        f"{spec['pace']}, {spec['travelers']} чел."
    )

    audit_structure(route, report)
    audit_duplicates(route, report)
    audit_schedule(route, draft, report)
    audit_pricing(route, draft, report)
    audit_content(route, report)
    audit_balance(route, draft, report)
    audit_transit(route, report)
    audit_spread(route, report)

    if verbose:
        report.render()
        print_itinerary(route)

    return report


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIOS),
        help="run a subset; repeatable (default: all)",
    )
    parser.add_argument("--verbose", action="store_true", help="print each itinerary")
    args = parser.parse_args()

    selected = args.scenario or sorted(SCENARIOS)
    reports: list[Report] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
        health = await client.get("/health")
        body = health.json()
        print(f"{BOLD}Health{RESET}: {json.dumps(body, ensure_ascii=False)}")
        if not body.get("opentripmap"):
            print(f"{RED}OPENTRIPMAP_API_KEY is missing — nothing to audit{RESET}")
            return 1

        for name in selected:
            print(f"\n{DIM}running {name}…{RESET}")
            report = await run_scenario(client, name, SCENARIOS[name], args.verbose)
            reports.append(report)
            if not args.verbose:
                report.render()

    errors = sum(len(r.errors) for r in reports)
    warnings = sum(len(r.warnings) for r in reports)
    print(
        f"\n{BOLD}Audit{RESET}: {len(reports)} scenario(s), "
        f"{errors} error(s), {warnings} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
