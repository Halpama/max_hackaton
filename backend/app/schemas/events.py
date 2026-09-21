from typing import Literal

from app.schemas.trip import CamelModel, RoutePlan

#: Must stay aligned with LOADING_STEPS in
#: web/src/features/trip-planner/model/mock.ts — index drives the loader UI.
STAGES: tuple[str, ...] = (
    "analyze",
    "places",
    "transit",
    "budget",
    "schedule",
)

STAGE_LABELS: dict[str, str] = {
    "analyze": "Анализ предпочтений",
    "places": "Подбор мест",
    "transit": "Расчёт времени в пути",
    "budget": "Распределение бюджета",
    "schedule": "Формирование расписания",
}


def stage_index(key: str) -> int:
    return STAGES.index(key)


class StageEvent(CamelModel):
    type: Literal["stage"] = "stage"
    key: str
    index: int
    label: str
    status: Literal["active", "done"]


class DoneEvent(CamelModel):
    type: Literal["done"] = "done"
    trip_id: str
    route: RoutePlan


class ErrorEvent(CamelModel):
    type: Literal["error"] = "error"
    trip_id: str
    message: str
    code: str = "generation_failed"
