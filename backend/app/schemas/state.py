from datetime import date as date_type
from typing import Literal

from pydantic import Field

from app.schemas.trip import CamelModel

LedgerKind = Literal["expense", "topup"]


class PackingBlock(CamelModel):
    """Mirrors PackingBlock in web/src/features/trip-planner/model/useTripLocalState.ts."""

    id: str
    type: Literal["text", "bullet", "check"]
    text: str = ""
    done: bool = False


class TripStateResponse(CamelModel):
    packing: list[PackingBlock]


class TripStateUpdate(CamelModel):
    packing: list[PackingBlock]


class LedgerEntryIn(CamelModel):
    kind: LedgerKind
    amount: int = Field(ge=1)
    title: str = ""
    date: date_type | None = None


class LedgerEntryOut(CamelModel):
    id: str
    kind: LedgerKind
    amount: int
    title: str
    date: str
    created_at: int


class FavoriteIds(CamelModel):
    ids: list[str]
