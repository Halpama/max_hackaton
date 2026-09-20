#!/usr/bin/env python
"""End-to-end smoke test against a running API with real GigaChat / OpenTripMap keys.

    python scripts/smoke.py
    python scripts/smoke.py --base-url http://localhost:8000 --city Казань
"""
import argparse
import asyncio
import json
import sys
from datetime import date, timedelta

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def ok(message: str) -> None:
    print(f"{GREEN}✓{RESET} {message}")


def fail(message: str) -> None:
    print(f"{RED}✗ {message}{RESET}")


def build_draft(city: str, days: int, budget: int, travelers: int) -> dict:
    start = date.today() + timedelta(days=14)
    end = start + timedelta(days=days - 1)
    return {
        "destination": city,
        "startDate": start.isoformat(),
        "startTime": "10:00",
        "endDate": end.isoformat(),
        "endTime": "18:00",
        "budget": budget,
        "travelers": travelers,
        "interests": ["sights", "museums", "gastro"],
        "pace": "medium",
        "findHousing": False,
    }


async def check_health(client: httpx.AsyncClient) -> bool:
    response = await client.get("/health")
    response.raise_for_status()
    body = response.json()
    print(f"\n{BOLD}Health{RESET}: {json.dumps(body, ensure_ascii=False)}")

    healthy = True
    for key, label in (
        ("redis", "Redis"),
        ("gigachat", "GIGACHAT_AUTH_KEY"),
        ("opentripmap", "OPENTRIPMAP_API_KEY"),
    ):
        if body.get(key):
            ok(f"{label} configured")
        else:
            fail(f"{label} missing — fill it in backend/.env")
            healthy = healthy and key == "gigachat"  # LLM is optional, keys are not
    return healthy


async def stream_generation(client: httpx.AsyncClient, trip_id: str) -> dict | None:
    """Consume the SSE stream and return the finished route."""
    print(f"\n{BOLD}Progress{RESET}")
    event_name = ""
    route: dict | None = None

    async with client.stream("GET", f"/api/v1/trips/{trip_id}/stream", timeout=300.0) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event_name = line[7:].strip()
                continue
            if not line.startswith("data: "):
                continue

            payload = json.loads(line[6:])
            if event_name == "stage":
                marker = "✓" if payload["status"] == "done" else "…"
                print(f"  {marker} {payload['index'] + 1}/5 {payload['label']}")
            elif event_name == "done":
                route = payload["route"]
                break
            elif event_name == "error":
                fail(f"Generation failed: {payload.get('message')}")
                return None

    return route


def print_route(route: dict) -> None:
    print(f"\n{BOLD}{route['city']}{RESET} · {route['dateLabel']} · {route['travelersLabel']} · {route['budgetLabel']}")

    places = route["places"]
    for day in route["days"]:
        print(f"\n  {BOLD}{day['label']}{RESET}")
        for index, activity in enumerate(day["activities"]):
            place = places.get(activity["placeId"], {})
            print(f"    {activity['time']}  {activity['title']}  {DIM}({activity['durationLabel']}){RESET}")
            print(f"           {DIM}{activity['meta']} · {place.get('address', '')}{RESET}")
            if index < len(day["transits"]) and day["transits"][index]:
                print(f"           {DIM}↓ {day['transits'][index]['label']}{RESET}")


def validate_route(route: dict, draft: dict) -> bool:
    """Assert the invariants the frontend relies on."""
    problems: list[str] = []
    places = route["places"]

    for field in ("city", "dateLabel", "travelersLabel", "budgetLabel", "days", "places"):
        if field not in route:
            problems.append(f"missing RoutePlan.{field}")

    if not route.get("days"):
        problems.append("no days generated")

    scheduled: list[str] = []
    for day in route.get("days", []):
        if not day["activities"]:
            problems.append(f"{day['label']} has no activities")
        if len(day["transits"]) != max(0, len(day["activities"]) - 1):
            problems.append(f"{day['label']}: {len(day['transits'])} transits for {len(day['activities'])} activities")

        times = [a["time"] for a in day["activities"]]
        if times != sorted(times):
            problems.append(f"{day['label']}: activities out of chronological order")

        for activity in day["activities"]:
            scheduled.append(activity["placeId"])
            if activity["placeId"] not in places:
                problems.append(f"activity {activity['id']} points at unknown place")

    if len(scheduled) != len(set(scheduled)):
        problems.append("a place is scheduled more than once")

    for place_id, place in places.items():
        if place.get("categoryKind") not in {"museum", "location", "food", "walk"}:
            problems.append(f"{place_id}: bad categoryKind {place.get('categoryKind')}")
        coords = place.get("coordinates") or []
        if len(coords) != 2 or not (-180 <= coords[0] <= 180 and -90 <= coords[1] <= 90):
            problems.append(f"{place_id}: bad coordinates {coords}")

    total = sum(place.get("priceValue") or 0 for place in places.values())
    if total > draft["budget"]:
        problems.append(f"planned spend {total} exceeds budget {draft['budget']}")

    print(f"\n{BOLD}Validation{RESET}")
    if problems:
        for problem in problems:
            fail(problem)
        return False

    ok(f"{len(route['days'])} days, {len(places)} places, planned spend {int(total)} ₽ of {draft['budget']} ₽")
    return True


async def check_side_endpoints(client: httpx.AsyncClient, trip_id: str, place_id: str) -> bool:
    print(f"\n{BOLD}Endpoints{RESET}")
    healthy = True

    listing = await client.get("/api/v1/trips")
    healthy &= listing.status_code == 200
    ok(f"GET /trips → {len(listing.json())} trip(s)")

    place = await client.get(f"/api/v1/places/{place_id}")
    healthy &= place.status_code == 200
    ok(f"GET /places/{place_id} → {place.json().get('title')}")

    await client.put(f"/api/v1/favorites/{place_id}")
    favorites = await client.get("/api/v1/favorites")
    healthy &= any(item["id"] == place_id for item in favorites.json())
    ok(f"favorites roundtrip → {len(favorites.json())} item(s)")
    await client.delete(f"/api/v1/favorites/{place_id}")

    await client.put(
        f"/api/v1/trips/{trip_id}/state",
        json={"packing": [{"id": "1", "type": "check", "text": "Паспорт", "done": False}]},
    )
    state = await client.get(f"/api/v1/trips/{trip_id}/state")
    healthy &= len(state.json()["packing"]) == 1
    ok("packing state persisted")

    entry = await client.post(
        f"/api/v1/trips/{trip_id}/ledger",
        json={"kind": "expense", "amount": 1200, "title": "Обед"},
    )
    healthy &= entry.status_code == 201
    await client.delete(f"/api/v1/trips/{trip_id}/ledger/{entry.json()['id']}")
    ok("ledger roundtrip")

    return bool(healthy)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--city", default="Санкт-Петербург")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--budget", type=int, default=45000)
    parser.add_argument("--travelers", type=int, default=2)
    args = parser.parse_args()

    draft = build_draft(args.city, args.days, args.budget, args.travelers)

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        if not await check_health(client):
            return 1

        print(f"\n{BOLD}Generating{RESET}: {args.city}, {args.days} дн., {args.budget} ₽, {args.travelers} чел.")
        created = await client.post("/api/v1/trips", json=draft)
        if created.status_code != 202:
            fail(f"POST /trips → {created.status_code} {created.text[:300]}")
            return 1

        trip_id = created.json()["id"]
        ok(f"trip {trip_id} accepted")

        route = await stream_generation(client, trip_id)
        if route is None:
            trip = await client.get(f"/api/v1/trips/{trip_id}")
            fail(f"No route. Trip state: {json.dumps(trip.json(), ensure_ascii=False)[:500]}")
            return 1

        print_route(route)
        if not validate_route(route, draft):
            return 1

        place_id = next(iter(route["places"]))
        if not await check_side_endpoints(client, trip_id, place_id):
            return 1

    print(f"\n{GREEN}{BOLD}Smoke test passed{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
