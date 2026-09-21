import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import set_user_context
from app.core.security import resolve_user
from app.db.models import Trip, User
from app.db.repositories import get_or_create_user, get_trip
from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    auth = resolve_user(authorization)
    user = await get_or_create_user(
        session,
        auth.max_user_id,
        username=auth.username,
        first_name=auth.first_name,
        last_name=auth.last_name,
    )
    set_user_context(user.id)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def owned_trip(trip_id: str, session: DbSession, user: CurrentUser) -> Trip:
    try:
        parsed = uuid.UUID(trip_id)
    except ValueError as exc:
        raise NotFoundError(f"Trip not found: {trip_id}") from exc

    trip = await get_trip(session, parsed, user.id)
    if trip is None:
        raise NotFoundError(f"Trip not found: {trip_id}")
    return trip


OwnedTrip = Annotated[Trip, Depends(owned_trip)]
