from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.clients import geocoding

router = APIRouter(prefix="/geo", tags=["geo"])


class CitySuggestion(BaseModel):
    name: str
    subtitle: str = ""
    label: str


class CitySuggestResponse(BaseModel):
    items: list[CitySuggestion] = Field(default_factory=list)


@router.get("/cities", response_model=CitySuggestResponse)
async def suggest_cities(
    q: str = Query("", max_length=80, description="Partial city name"),
) -> CitySuggestResponse:
    rows = await geocoding.suggest_cities(q, limit=8)
    return CitySuggestResponse(items=[CitySuggestion.model_validate(row) for row in rows])
