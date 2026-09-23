import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, status

from app.api.deps import DbSession, OwnedTrip
from app.core.errors import NotFoundError
from app.db.models import LedgerEntry
from app.db.repositories import (
    add_ledger_entry,
    delete_ledger_entry,
    get_or_create_trip_state,
    list_ledger,
)
from app.schemas.state import (
    LedgerEntryIn,
    LedgerEntryOut,
    TripStateResponse,
    TripStateUpdate,
)
from app.services.audit import record_event

router = APIRouter(prefix="/trips", tags=["trip-state"])

DEFAULT_TITLES = {"expense": "Трата", "topup": "Пополнение"}


def to_ledger_out(entry: LedgerEntry) -> LedgerEntryOut:
    created = entry.created_at or datetime.now(UTC)
    return LedgerEntryOut(
        id=str(entry.id),
        kind=entry.kind,
        amount=entry.amount,
        title=entry.title,
        date=entry.entry_date.isoformat(),
        # The frontend sorts by this, so hand it a millisecond timestamp.
        created_at=int(created.timestamp() * 1000),
    )


@router.get("/{trip_id}/state", response_model=TripStateResponse)
async def get_state(trip: OwnedTrip, session: DbSession) -> TripStateResponse:
    state = await get_or_create_trip_state(session, trip.id)
    return TripStateResponse.model_validate({"packing": state.packing or []})


@router.put("/{trip_id}/state", response_model=TripStateResponse)
async def put_state(
    trip: OwnedTrip, payload: TripStateUpdate, session: DbSession
) -> TripStateResponse:
    state = await get_or_create_trip_state(session, trip.id)
    state.packing = [block.model_dump(by_alias=True) for block in payload.packing]
    await record_event(
        "packing_updated",
        user_id=trip.user_id,
        trip_id=trip.id,
        session=session,
        payload={"blocks": len(payload.packing)},
    )
    return TripStateResponse(packing=payload.packing)


@router.get("/{trip_id}/ledger", response_model=list[LedgerEntryOut])
async def get_ledger(trip: OwnedTrip, session: DbSession) -> list[LedgerEntryOut]:
    return [to_ledger_out(entry) for entry in await list_ledger(session, trip.id)]


@router.post("/{trip_id}/ledger", response_model=LedgerEntryOut, status_code=status.HTTP_201_CREATED)
async def post_ledger(
    trip: OwnedTrip, payload: LedgerEntryIn, session: DbSession
) -> LedgerEntryOut:
    entry = await add_ledger_entry(
        session,
        trip.id,
        kind=payload.kind,
        amount=payload.amount,
        title=payload.title.strip() or DEFAULT_TITLES[payload.kind],
        entry_date=payload.date or date.today(),
    )
    await record_event(
        "expenses_updated",
        user_id=trip.user_id,
        trip_id=trip.id,
        session=session,
        payload={"action": "added", "kind": payload.kind, "amount": payload.amount},
    )
    return to_ledger_out(entry)


@router.delete("/{trip_id}/ledger/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ledger(trip: OwnedTrip, entry_id: str, session: DbSession) -> None:
    try:
        parsed = uuid.UUID(entry_id)
    except ValueError as exc:
        raise NotFoundError(f"Ledger entry not found: {entry_id}") from exc
    deleted = await delete_ledger_entry(session, trip.id, parsed)
    if not deleted:
        raise NotFoundError(f"Ledger entry not found: {entry_id}")
    await record_event(
        "expenses_updated",
        user_id=trip.user_id,
        trip_id=trip.id,
        session=session,
        payload={"action": "deleted", "entry_id": str(parsed)},
    )
