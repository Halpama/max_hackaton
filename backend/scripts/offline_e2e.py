#!/usr/bin/env python
"""Run the generation pipeline against the real Postgres and Redis, with the
external providers stubbed. Meant to be run inside the api container:

    docker compose exec -e OPENTRIPMAP_API_KEY=stub api \
        python scripts/offline_e2e.py --delay 6

It prints TRIP_ID immediately, then waits `--delay` seconds before generating, so
you can attach to `/api/v1/trips/<id>/stream` from the host and confirm the SSE
endpoint receives progress published by this separate process.
"""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path

import respx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cache.redis import get_redis  # noqa: E402
from app.db.models import Trip  # noqa: E402
from app.db.repositories import get_or_create_user  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.schemas.trip import TripDraft  # noqa: E402
from app.services.pipeline import generate_trip, parse_draft_bounds  # noqa: E402
from tests.fixtures import SAMPLE_DRAFT, mock_external_apis  # noqa: E402

#: The stubs answer on the same cache keys as the real providers, so leaving
#: them behind would make the next real generation build a trip out of fixtures
#: ("Тестовая улица 1" in every card). Everything here is re-fetchable.
#: `otm:quota:*` is deliberately absent — that counter must survive.
STUB_CACHE_PATTERNS = (
    "otm:geoname:*",
    "otm:radius:*",
    "otm:xid:*",
    "osrm:*",
    "gigachat:completion:*",
    "trip:plan:*",
)


async def clear_stub_cache() -> int:
    redis = await get_redis()
    removed = 0

    for pattern in STUB_CACHE_PATTERNS:
        keys = [key async for key in redis.scan_iter(match=pattern)]
        if keys:
            removed += await redis.delete(*keys)

    return removed


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()

    draft = TripDraft.model_validate(SAMPLE_DRAFT)
    start_at, end_at = parse_draft_bounds(draft)

    async with get_session_factory()() as session:
        user = await get_or_create_user(session, 1, first_name="Dev")
        trip = Trip(
            id=uuid.uuid4(),
            user_id=user.id,
            destination=draft.destination,
            start_at=start_at,
            end_at=end_at,
            budget=draft.budget,
            travelers=draft.travelers,
            interests=list(draft.interests),
            pace=draft.pace,
            find_housing=False,
            status="pending",
        )
        session.add(trip)
        await session.commit()
        trip_id = trip.id

    print(f"TRIP_ID={trip_id}", flush=True)

    if args.delay:
        await asyncio.sleep(args.delay)

    try:
        with respx.mock(assert_all_called=False) as router:
            mock_external_apis(router)
            await generate_trip(trip_id, draft)
    finally:
        print(f"CACHE_CLEARED={await clear_stub_cache()}", flush=True)

    async with get_session_factory()() as session:
        refreshed = await session.get(Trip, trip_id)
        print(f"STATUS={refreshed.status}", flush=True)
        if refreshed.status != "ready":
            print(f"ERROR={refreshed.error}", flush=True)
            return 1
        print(f"DAYS={len(refreshed.route_plan['days'])}", flush=True)
        print(f"PLACES={len(refreshed.route_plan['places'])}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
