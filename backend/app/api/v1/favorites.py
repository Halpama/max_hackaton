from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.db.repositories import (
    add_favorite,
    get_places,
    list_favorite_ids,
    remove_favorite,
)
from app.schemas.trip import Place

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[Place])
async def get_favorites(session: DbSession, user: CurrentUser) -> list[Place]:
    """Favourite places, newest first. Unknown ids are skipped."""
    ids = await list_favorite_ids(session, user.id)
    if not ids:
        return []

    by_id = {row.external_id: row for row in await get_places(session, ids)}
    return [
        Place.model_validate(by_id[place_id].payload)
        for place_id in ids
        if place_id in by_id
    ]


@router.put("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def put_favorite(place_id: str, session: DbSession, user: CurrentUser) -> None:
    await add_favorite(session, user.id, place_id)


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(place_id: str, session: DbSession, user: CurrentUser) -> None:
    await remove_favorite(session, user.id, place_id)
