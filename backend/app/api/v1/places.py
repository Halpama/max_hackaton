from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.errors import NotFoundError
from app.db.repositories import get_place
from app.schemas.trip import Place

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/{place_id}", response_model=Place)
async def get_place_by_id(place_id: str, session: DbSession) -> Place:
    """Resolve a place saved from any previously generated itinerary."""
    row = await get_place(session, place_id)
    if row is None:
        raise NotFoundError(f"Place not found: {place_id}")
    return Place.model_validate(row.payload)
