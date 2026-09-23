"""Five-stage route generation, streaming progress as it goes.

Stage keys match LOADING_STEPS in the frontend, so the loader screen advances in
step with the real work instead of a timer.
"""
import uuid
from time import perf_counter
from datetime import datetime, timedelta

import orjson
from sqlalchemy import select

from app.cache import keys
from app.cache.decorator import cached_json
from app.clients.geocoding import in_russia, resolve_coords
from app.clients.opentripmap import opentripmap
from app.clients.weather import weather as weather_client
from app.core.config import settings
from app.core.errors import AppError, NotFoundError, UpstreamError
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
from app.services.audit import record_event
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


def _coords_ok(geo: dict) -> bool:
    try:
        lat, lon = float(geo["lat"]), float(geo["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    country = str(geo.get("country") or "").upper()
    if country and country != "RU":
        return False
    return in_russia(lat, lon)


async def _resolve_trip_coords(
    *,
    draft_destination: str,
    city: str,
    geo_query: str,
) -> tuple[float, float]:
    """Resolve itinerary centre inside Russia.

    Open-Meteo (RU) first — same source as city autocomplete — so an LLM
    latinisation cannot send the route to Africa via OpenTripMap geoname.
    """
    queries: list[str] = []
    for value in (draft_destination, city, geo_query):
        cleaned = (value or "").strip()
        if cleaned and cleaned.casefold() not in {q.casefold() for q in queries}:
            queries.append(cleaned)

    last_error: Exception | None = None
    for query in queries:
        try:
            geo = await resolve_coords(query)
            if _coords_ok(geo):
                return float(geo["lat"]), float(geo["lon"])
            logger.warning(
                "Rejecting out-of-Russia coords for %s: %s,%s",
                query,
                geo.get("lat"),
                geo.get("lon"),
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Open-Meteo resolve failed for %s: %s", query, exc)

    for query in queries:
        try:
            geo = await opentripmap.geoname(query)
            if _coords_ok(geo):
                return float(geo["lat"]), float(geo["lon"])
            logger.warning(
                "OpenTripMap geoname outside Russia for %s: %s,%s country=%s",
                query,
                geo.get("lat"),
                geo.get("lon"),
                geo.get("country"),
            )
        except (UpstreamError, NotFoundError, AppError) as exc:
            last_error = exc
            logger.warning("OpenTripMap geoname failed for %s: %s", query, exc)

    raise NotFoundError(
        f"Не удалось найти координаты для «{city or draft_destination}»"
    ) from last_error


async def build_route(
    draft: TripDraft,
    trip_id: uuid.UUID,
    *,
    emit: bool = True,
    generation_id: uuid.UUID | None = None,
    user_id: int | None = None,
    stage_context: dict[str, str | None] | None = None,
) -> RoutePlan:
    """Run the pipeline and return the finished plan."""

    async def stage_start(key: str) -> None:
        if stage_context is not None:
            stage_context["key"] = key
            stage_context["started"] = str(perf_counter())
        if emit:
            await _emit(trip_id, key, "active")
        await _set_status(trip_id, stage=key)
        await record_event(
            "stage_started",
            user_id=user_id,
            trip_id=trip_id,
            generation_id=generation_id,
            stage=key,
            status="started",
        )

    async def stage_done(key: str) -> None:
        if emit:
            await _emit(trip_id, key, "done")
        started = float(stage_context["started"]) if stage_context and stage_context.get("started") else None
        await record_event(
            "stage_completed",
            user_id=user_id,
            trip_id=trip_id,
            generation_id=generation_id,
            stage=key,
            status="completed",
            duration_ms=round((perf_counter() - started) * 1000, 2) if started else None,
        )

    start_at, end_at = parse_draft_bounds(draft)
    slots = build_day_slots(start_at, end_at)

    # 1. Анализ предпочтений
    await stage_start("analyze")
    analysis = await llm.analyze_destination(draft)
    city = analysis["city"]
    await stage_done("analyze")

    # 2. Подбор мест
    await stage_start("places")
    lat, lon = await _resolve_trip_coords(
        draft_destination=draft.destination,
        city=city,
        geo_query=str(analysis.get("geoQuery") or ""),
    )

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
    if draft.budget <= 0:
        # 0 ₽ is an explicit free-only trip, not "budget unspecified".
        free = [c for c in candidates if budget_service.is_free_candidate(c)]
        if free:
            candidates = free
    if not candidates:
        raise NotFoundError(f"Не удалось найти места для «{city}»")

    selected = await llm.curate_places(draft, candidates, min(needed, len(candidates)))
    # One meal per day when food was asked for, none of it otherwise.
    # Free-only trips skip paid meals even if gastro was selected.
    food_wanted = (
        0
        if draft.budget <= 0
        else (len(slots) if "gastro" in draft.interests else 0)
    )
    selected = balance_food(selected, candidates, wanted=food_wanted)
    if draft.budget <= 0:
        selected = [c for c in selected if budget_service.is_free_candidate(c)] or selected
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
    generation_id = uuid.uuid4()
    started = perf_counter()
    stage_context: dict[str, str | None] = {"key": None, "started": None}
    async with get_session_factory()() as session:
        trip = await session.scalar(select(Trip).where(Trip.id == trip_id))
        user_id = trip.user_id if trip is not None else None
    safe_parameters = {
        "destination": draft.destination,
        "start_date": draft.start_date,
        "start_time": draft.start_time,
        "end_date": draft.end_date,
        "end_time": draft.end_time,
        "budget": draft.budget,
        "travelers": draft.travelers,
        "interests": list(draft.interests),
        "pace": draft.pace,
        "find_housing": draft.find_housing,
    }
    await record_event(
        "trip_generation_started",
        user_id=user_id,
        trip_id=trip_id,
        generation_id=generation_id,
        status="started",
        payload={"parameters": safe_parameters},
    )
    await _set_status(trip_id, status="running")

    try:
        cache_key = plan_cache_key(draft)

        async def produce() -> dict:
            route = await build_route(
                draft,
                trip_id,
                generation_id=generation_id,
                user_id=user_id,
                stage_context=stage_context,
            )
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
                await record_event(
                    "stage_started",
                    user_id=user_id,
                    trip_id=trip_id,
                    generation_id=generation_id,
                    stage=key,
                    status="started",
                    payload={"cache_hit": True},
                )
                await _emit(trip_id, key, "done")
                await record_event(
                    "stage_completed",
                    user_id=user_id,
                    trip_id=trip_id,
                    generation_id=generation_id,
                    stage=key,
                    status="completed",
                    duration_ms=0,
                    payload={"cache_hit": True},
                )

        await progress.publish(
            trip_id,
            DoneEvent(trip_id=str(trip_id), route=route).model_dump(by_alias=True),
        )
        logger.info("Trip %s generated: %d days", trip_id, len(route.days))
        await record_event(
            "trip_generation_completed",
            user_id=user_id,
            trip_id=trip_id,
            generation_id=generation_id,
            status="completed",
            duration_ms=round((perf_counter() - started) * 1000, 2),
            payload={"days": len(route.days)},
        )

    except Exception as exc:  # noqa: BLE001 - the failure must reach the client
        message = exc.message if isinstance(exc, AppError) else "Не удалось построить маршрут"
        logger.exception("Trip %s generation failed", trip_id)
        if stage_context.get("key"):
            stage_started = float(stage_context["started"]) if stage_context.get("started") else None
            await record_event(
                "stage_failed",
                user_id=user_id,
                trip_id=trip_id,
                generation_id=generation_id,
                stage=stage_context["key"],
                status="failed",
                duration_ms=round((perf_counter() - stage_started) * 1000, 2) if stage_started else None,
                error=exc,
            )
        await record_event(
            "trip_generation_failed",
            user_id=user_id,
            trip_id=trip_id,
            generation_id=generation_id,
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000, 2),
            error=exc,
        )
        await _set_status(trip_id, status="failed", error=str(exc))
        await progress.publish(
            trip_id,
            ErrorEvent(trip_id=str(trip_id), message=message).model_dump(by_alias=True),
        )
