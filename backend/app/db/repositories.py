import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Favorite, LedgerEntry, Place, Trip, TripState, User
from app.schemas.trip import Place as PlaceSchema


async def get_or_create_user(
    session: AsyncSession,
    max_user_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    user = await session.scalar(select(User).where(User.max_user_id == max_user_id))
    if user is not None:
        return user

    user = User(
        max_user_id=max_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    await session.flush()
    return user


async def get_trip(session: AsyncSession, trip_id: uuid.UUID, user_id: int) -> Trip | None:
    return await session.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.user_id == user_id,
            Trip.archived.is_(False),
        )
    )


async def list_trips(session: AsyncSession, user_id: int) -> list[Trip]:
    result = await session.scalars(
        select(Trip)
        .where(Trip.user_id == user_id, Trip.archived.is_(False))
        .order_by(Trip.created_at.desc())
    )
    return list(result)


async def archive_trip(session: AsyncSession, trip: Trip) -> None:
    """Hide a trip from the home list without deleting related data."""
    trip.archived = True
    await session.commit()


async def upsert_places(
    session: AsyncSession, places: list[PlaceSchema], city: str
) -> None:
    """Store the places of a generated plan so favourites can resolve them later."""
    if not places:
        return

    external_ids = [place.id for place in places]
    existing = {
        row.external_id: row
        for row in await session.scalars(
            select(Place).where(Place.external_id.in_(external_ids))
        )
    }

    for place in places:
        payload = place.model_dump(by_alias=True)
        row = existing.get(place.id)
        if row is None:
            session.add(
                Place(
                    external_id=place.id,
                    title=place.title,
                    city=place.city or city,
                    payload=payload,
                )
            )
        else:
            row.title = place.title
            row.city = place.city or city
            row.payload = payload


async def get_place(session: AsyncSession, external_id: str) -> Place | None:
    return await session.scalar(
        select(Place).where(Place.external_id == external_id)
    )


async def get_places(session: AsyncSession, external_ids: list[str]) -> list[Place]:
    if not external_ids:
        return []
    result = await session.scalars(
        select(Place).where(Place.external_id.in_(external_ids))
    )
    return list(result)


async def list_favorite_ids(session: AsyncSession, user_id: int) -> list[str]:
    result = await session.scalars(
        select(Favorite.place_external_id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    return list(result)


async def add_favorite(session: AsyncSession, user_id: int, external_id: str) -> None:
    exists = await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id, Favorite.place_external_id == external_id
        )
    )
    if exists is None:
        session.add(Favorite(user_id=user_id, place_external_id=external_id))


async def remove_favorite(session: AsyncSession, user_id: int, external_id: str) -> None:
    await session.execute(
        delete(Favorite).where(
            Favorite.user_id == user_id, Favorite.place_external_id == external_id
        )
    )


async def get_or_create_trip_state(session: AsyncSession, trip_id: uuid.UUID) -> TripState:
    state = await session.scalar(select(TripState).where(TripState.trip_id == trip_id))
    if state is None:
        state = TripState(trip_id=trip_id, packing=[])
        session.add(state)
        await session.flush()
    return state


async def list_ledger(session: AsyncSession, trip_id: uuid.UUID) -> list[LedgerEntry]:
    result = await session.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.trip_id == trip_id)
        .order_by(LedgerEntry.entry_date.desc(), LedgerEntry.created_at.desc())
    )
    return list(result)


async def add_ledger_entry(
    session: AsyncSession,
    trip_id: uuid.UUID,
    *,
    kind: str,
    amount: int,
    title: str,
    entry_date: date,
) -> LedgerEntry:
    entry = LedgerEntry(
        trip_id=trip_id,
        kind=kind,
        amount=amount,
        title=title,
        entry_date=entry_date,
    )
    session.add(entry)
    await session.flush()
    return entry


async def delete_ledger_entry(
    session: AsyncSession, trip_id: uuid.UUID, entry_id: uuid.UUID
) -> bool:
    result = await session.execute(
        delete(LedgerEntry).where(
            LedgerEntry.trip_id == trip_id, LedgerEntry.id == entry_id
        )
    )
    return result.rowcount > 0
