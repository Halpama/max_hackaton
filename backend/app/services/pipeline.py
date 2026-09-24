"""Five-stage route generation, streaming progress as it goes.

Stage keys match LOADING_STEPS in the frontend, so the loader screen advances in
step with the real work instead of a timer.
"""
import uuid
from datetime import datetime, timedelta

import orjson
from sqlalchemy import select

from app.cache import keys
from app.cache.decorator import cached_json
from app.clients.opentripmap import opentripmap
from app.clients.weather import weather as weather_client
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Trip
from app.db.repositories import upsert_places
from app.db.session import get_session_factory
from app.schemas.events import STAGE_LABELS, STAGES, DoneEvent, ErrorEvent, StageEvent
from app.schemas.trip import (
    Activity,
    DayPlan,
    DayWeather,
    Place,
    RoutePlan,
    TransitLeg,
    TripDraft,
)
from app.services import budget as budget_service
from app.services import formatting, llm, opening_hours, progress, transit
from app.services.places import PlaceCandidate, balance_food, collect_candidates
from app.services.scheduler import (
    PACE_ACTIVITY_COUNT,
    allocate_stays,
    build_day_slots,
    distribute,
)

logger = get_logger(__name__)

#: Hard ceiling on places per trip — keeps OpenTripMap detail calls bounded.
MAX_PLACES = 24


def round_to_five(value: datetime) -> datetime:
    """Nudge a schedule time to the next 5-minute mark — 10:57 reads badly."""
    remainder = value.minute % 5
    if remainder == 0:
        return value.replace(second=0, microsecond=0)
    return (value + timedelta(minutes=5 - remainder)).replace(second=0, microsecond=0)


def parse_draft_bounds(draft: TripDraft) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(f"{draft.start_date}T{draft.start_time}")
    end = datetime.fromisoformat(f"{draft.end_date}T{draft.end_time}")
    if end <= start:
        end = start + timedelta(hours=12)
    return start, end


def plan_cache_key(draft: TripDraft) -> str:
    """Identical drafts reuse a plan instead of spending API quota again."""
    payload = draft.model_dump(by_alias=True)
    payload["interests"] = sorted(payload.get("interests") or [])
    return keys.trip_plan(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS))


async def _emit(trip_id: uuid.UUID, key: str, status: str) -> None:
    event = StageEvent(
        key=key,
        index=STAGES.index(key),
        label=STAGE_LABELS[key],
        status=status,
    )
    await progress.publish(trip_id, event.model_dump(by_alias=True))


async def _set_status(
    trip_id: uuid.UUID,
    *,
    status: str | None = None,
    stage: str | None = None,
    error: str | None = None,
    route_plan: dict | None = None,
) -> None:
    async with get_session_factory()() as session:
        trip = await session.scalar(select(Trip).where(Trip.id == trip_id))
        if trip is None:
            return
        if status is not None:
            trip.status = status
        if stage is not None:
            trip.stage = stage
        if error is not None:
            trip.error = error
        if route_plan is not None:
            trip.route_plan = route_plan
        await session.commit()


async def _day_forecast(*, lat: float, lon: float, slots: list) -> dict[str, DayWeather]:
    """Forecast keyed by ISO date, empty for trips beyond the forecast horizon."""
    if not settings.weather_enabled or not slots:
        return {}

    raw = await weather_client.daily(
        lat=lat,
        lon=lon,
        start=slots[0].start.date(),
        end=slots[-1].start.date(),
    )
    return {iso: DayWeather(**payload) for iso, payload in raw.items()}


async def build_route(
    draft: TripDraft,
    trip_id: uuid.UUID,
    *,
    emit: bool = True,
) -> RoutePlan:
    """Run the pipeline and return the finished plan."""

    async def stage_start(key: str) -> None:
        if emit:
            await _emit(trip_id, key, "active")
        await _set_status(trip_id, stage=key)

    async def stage_done(key: str) -> None:
        if emit:
            await _emit(trip_id, key, "done")

    start_at, end_at = parse_draft_bounds(draft)
    slots = build_day_slots(start_at, end_at)

    # 1. Анализ предпочтений
    await stage_start("analyze")
    analysis = await llm.analyze_destination(draft)
    city = analysis["city"]
    await stage_done("analyze")

    # 2. Подбор мест
    await stage_start("places")
    geo = await opentripmap.geoname(analysis["geoQuery"])
    lat, lon = float(geo["lat"]), float(geo["lon"])

    per_day = PACE_ACTIVITY_COUNT.get(draft.pace, 5)
    needed = max(3, min(MAX_PLACES, per_day * len(slots)))

    candidates = await collect_candidates(
        city=city,
        lat=lat,
        lon=lon,
        interests=draft.interests,
        needed=needed,
        radius_meters=analysis["radiusMeters"],
    )
    if not candidates:
        raise NotFoundError(f"Не удалось найти места для «{city}»")

    selected = await llm.curate_places(draft, candidates, min(needed, len(candidates)))
    # One meal per day when food was asked for, none of it otherwise.
    selected = balance_food(
        selected, candidates, wanted=len(slots) if "gastro" in draft.interests else 0
    )
    await stage_done("places")

    # 3. Расчёт времени в пути
    await stage_start("transit")
    grouped = distribute(selected, slots, draft.pace)
    metro = transit.has_metro(city)
    day_transits: list[list[TransitLeg | None]] = []
    day_transit_minutes: list[list[int]] = []

    for day in grouped:
        legs: list[TransitLeg | None] = []
        minutes: list[int] = []
        for index in range(len(day) - 1):
            leg, leg_minutes = await transit.build_leg(
                day[index].coordinates,
                day[index + 1].coordinates,
                metro=metro,
            )
            legs.append(leg)
            minutes.append(leg_minutes)
        day_transits.append(legs)
        day_transit_minutes.append(minutes)
    await stage_done("transit")

    # 4. Распределение бюджета
    await stage_start("budget")
    used = [c for day in grouped for c in day]
    scale = budget_service.compute_scale(used, draft.budget, draft.travelers)
    prices: dict[str, tuple[float | None, str]] = {
        c.xid: budget_service.price_for(c, scale=scale, travelers=draft.travelers)
        for c in used
    }
    await stage_done("budget")

    # 5. Формирование расписания
    await stage_start("schedule")
    forecast = await _day_forecast(lat=lat, lon=lon, slots=slots)
    places: dict[str, Place] = {}
    days: list[DayPlan] = []

    for day_index, (slot, day_places) in enumerate(zip(slots, grouped, strict=False)):
        cursor = round_to_five(slot.start)
        activities: list[Activity] = []
        transit_for_day = day_transit_minutes[day_index]
        stays = allocate_stays(
            day_places, draft.pace, slot.minutes, transit_for_day
        )

        for position, (candidate, stay) in enumerate(
            zip(day_places, stays, strict=True)
        ):
            visit_start, finish, stay = opening_hours.fit_visit(
                cursor,
                stay,
                opening_hours=candidate.opening_hours,
                day_end=slot.end,
            )
            # If hours pushed the start later (place still closed), honour that.
            cursor = visit_start
            price_value, price_text, price_estimated = prices.get(
                candidate.xid, (None, "Бесплатно", False)
            )

            places[candidate.xid] = Place(
                id=candidate.xid,
                title=candidate.title,
                category=candidate.category,
                category_kind=candidate.category_kind,
                environment_kind=candidate.environment_kind,
                city=candidate.city,
                price_label=price_text,
                price_value=price_value,
                price_estimated=price_estimated,
                duration_label=formatting.duration_label(stay),
                time_range=formatting.time_range_label(cursor, finish),
                rating=candidate.rating,
                reviews_label=candidate.reviews_label,
                rating_source=candidate.rating_source,
                address=candidate.address,
                description=candidate.description,
                image_url=candidate.image_url,
                opening_hours=candidate.opening_hours,
                source_url=candidate.source_url,
                source_name=candidate.source_name,
                coordinates=candidate.coordinates,
            )

            activities.append(
                Activity(
                    id=f"{day_index + 1}-{position + 1}-{candidate.xid}",
                    place_id=candidate.xid,
                    time=formatting.time_label(cursor),
                    duration_label=formatting.duration_label(stay),
                    title=candidate.title,
                    meta=f"{candidate.category} • {price_text}",
                )
            )

            cursor = finish
            if position < len(transit_for_day):
                cursor += timedelta(minutes=transit_for_day[position])
            cursor = round_to_five(cursor)

        day_date = slot.start.date()
        days.append(
            DayPlan(
                id=f"day-{day_index + 1}",
                label=f"День {day_index + 1}",
                date=day_date.isoformat(),
                date_label=formatting.weekday_label(day_date),
                activities=activities,
                transits=day_transits[day_index],
                weather=forecast.get(day_date.isoformat()),
            )
        )

    route = RoutePlan(
        city=city,
        date_label=formatting.date_range_label(start_at.date(), end_at.date()),
        travelers_label=formatting.travelers_label(draft.travelers),
        budget_label=budget_service.budget_label(draft.budget),
        days=[day for day in days if day.activities] or days[:1],
        places=places,
    )
    await stage_done("schedule")

    return route


async def generate_trip(trip_id: uuid.UUID, draft: TripDraft) -> None:
    """Background entrypoint: generate, persist, and announce the result."""
    await _set_status(trip_id, status="running")

    try:
        cache_key = plan_cache_key(draft)

        async def produce() -> dict:
            route = await build_route(draft, trip_id)
            return route.model_dump(by_alias=True)

        payload = await cached_json(cache_key, keys.TTL_PLAN, produce)
        route = RoutePlan.model_validate(payload)

        async with get_session_factory()() as session:
            trip = await session.scalar(select(Trip).where(Trip.id == trip_id))
            if trip is not None:
                trip.status = "ready"
                trip.stage = "schedule"
                trip.error = None
                trip.route_plan = payload
            await upsert_places(session, list(route.places.values()), route.city)
            await session.commit()

        # A cache hit skips build_route, so replay the stages for the loader.
        history = await progress.history(trip_id)
        if not any(event.get("type") == "stage" for event in history):
            for key in STAGES:
                await _emit(trip_id, key, "done")

        await progress.publish(
            trip_id,
            DoneEvent(trip_id=str(trip_id), route=route).model_dump(by_alias=True),
        )
        logger.info("Trip %s generated: %d days", trip_id, len(route.days))

    except Exception as exc:  # noqa: BLE001 - the failure must reach the client
        message = exc.message if isinstance(exc, AppError) else "Не удалось построить маршрут"
        logger.exception("Trip %s generation failed", trip_id)
        await _set_status(trip_id, status="failed", error=str(exc))
        await progress.publish(
            trip_id,
            ErrorEvent(trip_id=str(trip_id), message=message).model_dump(by_alias=True),
        )
