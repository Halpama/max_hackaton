import asyncio
import uuid
from collections.abc import AsyncIterator

import orjson
from fastapi import APIRouter, Header, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, OwnedTrip
from app.cache import keys
from app.cache.redis import get_redis
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.security import resolve_user
from app.db.models import Trip, User
from app.db.repositories import list_trips, archive_trip
from app.db.session import get_session_factory
from app.schemas.trip import (
    RoutePlan,
    TripCreated,
    TripDraft,
    TripResponse,
    TripSummary,
)
from app.services import formatting, progress
from app.services.audit import record_event
from app.services.budget import budget_label
from app.services.pipeline import generate_trip, parse_draft_bounds

logger = get_logger(__name__)
router = APIRouter(prefix="/trips", tags=["trips"])

#: asyncio only keeps weak references to tasks; hold them so they are not collected.
_background_tasks: set[asyncio.Task] = set()

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # Tell nginx and friends not to buffer the stream.
    "X-Accel-Buffering": "no",
}


def trip_to_draft(trip: Trip) -> TripDraft:
    return TripDraft(
        destination=trip.destination,
        start_date=trip.start_at.date().isoformat(),
        start_time=f"{trip.start_at.hour:02d}:{trip.start_at.minute:02d}",
        end_date=trip.end_at.date().isoformat(),
        end_time=f"{trip.end_at.hour:02d}:{trip.end_at.minute:02d}",
        budget=trip.budget,
        adults=trip.adults,
        children=trip.children,
        interests=list(trip.interests or []),
        pace=trip.pace,
        find_housing=trip.find_housing,
    )


def trip_to_response(trip: Trip) -> TripResponse:
    route = RoutePlan.model_validate(trip.route_plan) if trip.route_plan else None
    return TripResponse(
        id=str(trip.id),
        status=trip.status,
        stage=trip.stage,
        error=trip.error,
        draft=trip_to_draft(trip),
        route=route,
    )


def trip_to_summary(trip: Trip) -> TripSummary:
    city = (trip.route_plan or {}).get("city") or trip.destination
    return TripSummary(
        id=str(trip.id),
        city=city,
        date_label=formatting.short_date_range_label(trip.start_at.date(), trip.end_at.date()),
        travelers_label=formatting.travelers_short_label(trip.adults, trip.children),
        budget_label=budget_label(trip.budget),
        status=trip.status,
    )


def _spawn(trip_id: uuid.UUID, draft: TripDraft) -> None:
    task = asyncio.create_task(generate_trip(trip_id, draft))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("", response_model=TripCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_trip(draft: TripDraft, session: DbSession, user: CurrentUser) -> TripCreated:
    """Register the trip and kick off generation; progress arrives over SSE."""
    start_at, end_at = parse_draft_bounds(draft)

    trip = Trip(
        id=uuid.uuid4(),
        user_id=user.id,
        destination=draft.destination.strip(),
        start_at=start_at,
        end_at=end_at,
        budget=draft.budget,
        travelers=draft.travelers,
        adults=draft.adults,
        children=draft.children,
        interests=list(draft.interests),
        pace=draft.pace,
        find_housing=draft.find_housing,
        status="pending",
    )
    session.add(trip)
    await session.commit()

    await record_event(
        "trip_created",
        user_id=user.id,
        trip_id=trip.id,
        session=session,
        payload={
            "destination": trip.destination,
            "travelers": trip.travelers,
            "adults": trip.adults,
            "children": trip.children,
        },
    )

    _spawn(trip.id, draft)
    return TripCreated(id=str(trip.id), status="pending")


@router.get("", response_model=list[TripSummary])
async def get_trips(session: DbSession, user: CurrentUser) -> list[TripSummary]:
    return [trip_to_summary(trip) for trip in await list_trips(session, user.id)]


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip_by_id(trip: OwnedTrip) -> TripResponse:
    return trip_to_response(trip)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip: OwnedTrip, session: DbSession) -> None:
    """Soft-hide the trip. Places, favourites and plan caches stay untouched."""
    await archive_trip(session, trip)
    await record_event(
        "trip_archived", user_id=trip.user_id, trip_id=trip.id, session=session
    )


@router.post("/{trip_id}/retry", response_model=TripCreated)
async def retry_trip(trip: OwnedTrip, session: DbSession) -> TripCreated:
    """Re-run generation for a trip that failed."""
    draft = trip_to_draft(trip)
    trip.status = "pending"
    trip.stage = None
    trip.error = None
    await session.commit()
    await record_event(
        "trip_updated",
        user_id=trip.user_id,
        trip_id=trip.id,
        session=session,
        payload={"action": "retry"},
    )

    # Drop the old progress log so the loader does not replay the failed run.
    try:
        redis = await get_redis()
        await redis.delete(keys.trip_progress_log(trip.id), f"trip:{trip.id}:seq")
    except Exception as exc:  # noqa: BLE001 - stale progress is not fatal
        logger.warning("Could not reset progress for %s: %s", trip.id, exc)

    _spawn(trip.id, draft)
    return TripCreated(id=str(trip.id), status="pending")


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {orjson.dumps(payload).decode()}\n\n"


@router.get("/{trip_id}/stream")
async def stream_trip(
    trip_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> StreamingResponse:
    """Server-sent events with the real generation progress.

    Authorisation and the ownership check run up front against a short-lived
    session so the stream itself never holds a database connection open.
    """
    auth = resolve_user(authorization)

    try:
        parsed_id = uuid.UUID(trip_id)
    except ValueError as exc:
        raise NotFoundError(f"Trip not found: {trip_id}") from exc

    async with get_session_factory()() as session:
        user = await session.scalar(select(User).where(User.max_user_id == auth.max_user_id))
        if user is None:
            raise NotFoundError(f"Trip not found: {trip_id}")
        trip = await session.scalar(
            select(Trip).where(
                Trip.id == parsed_id,
                Trip.user_id == user.id,
                Trip.archived.is_(False),
            )
        )
        if trip is None:
            raise NotFoundError(f"Trip not found: {trip_id}")
        finished = trip.status in {"ready", "failed"}
        route_plan = trip.route_plan
        error = trip.error

    async def publisher() -> AsyncIterator[str]:
        # A trip that finished before the client connected replays from the database.
        if finished and route_plan:
            for event in await progress.history(parsed_id):
                if event.get("type") == "stage":
                    yield _sse("stage", event)
            yield _sse("done", {"type": "done", "tripId": trip_id, "route": route_plan})
            return

        if finished and not route_plan:
            yield _sse(
                "error",
                {
                    "type": "error",
                    "tripId": trip_id,
                    "message": error or "Не удалось построить маршрут",
                    "code": "generation_failed",
                },
            )
            return

        try:
            async for event in progress.stream(parsed_id):
                if await request.is_disconnected():
                    break
                event_type = event.get("type", "message")
                if event_type == "ping":
                    yield ": ping\n\n"
                    continue
                yield _sse(event_type, event)
        except asyncio.CancelledError:  # client went away
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("SSE stream for %s failed", trip_id)
            yield _sse(
                "error",
                {
                    "type": "error",
                    "tripId": trip_id,
                    "message": "Поток прогресса прервался",
                    "code": "stream_failed",
                    "details": str(exc),
                },
            )

    return StreamingResponse(
        publisher(), media_type="text/event-stream", headers=SSE_HEADERS
    )
