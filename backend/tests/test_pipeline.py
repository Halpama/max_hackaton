import uuid

import pytest
import respx

from app.schemas.trip import TripDraft
from app.services.pipeline import build_route
from tests.fixtures import SAMPLE_DRAFT, mock_external_apis


@pytest.fixture
def draft() -> TripDraft:
    return TripDraft.model_validate(SAMPLE_DRAFT)


@respx.mock
async def test_build_route_produces_a_usable_plan(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    assert route.city == "Санкт-Петербург"
    assert route.travelers_label == "2 путешественника"
    assert route.budget_label == "~45 000 ₽"
    assert route.date_label == "15–17 сентября"
    assert len(route.days) >= 1

    # Every activity resolves to a place, and each day has one transit per gap.
    for day in route.days:
        assert day.activities
        assert len(day.transits) == len(day.activities) - 1
        for activity in day.activities:
            assert activity.place_id in route.places

    # No place is scheduled twice across the trip.
    scheduled = [a.place_id for day in route.days for a in day.activities]
    assert len(scheduled) == len(set(scheduled))


@respx.mock
async def test_times_advance_within_each_day(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    for day in route.days:
        times = [a.time for a in day.activities]
        assert times == sorted(times), f"Activities out of order: {times}"

    first = route.days[0].activities[0]
    assert first.time == "10:00", "Day one must start at the arrival time"


@respx.mock
async def test_budget_stays_within_the_declared_amount(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    total = sum(place.price_value or 0 for place in route.places.values())
    assert total <= draft.budget, f"Planned spend {total} exceeds budget {draft.budget}"

    for place in route.places.values():
        if place.price_value:
            assert "₽" in place.price_label
        else:
            assert place.price_label == "Бесплатно"


@respx.mock
async def test_pace_controls_activities_per_day(draft: TripDraft):
    mock_external_apis(respx.mock)

    calm = await build_route(
        draft.model_copy(update={"pace": "calm"}), uuid.uuid4(), emit=False
    )
    active = await build_route(
        draft.model_copy(update={"pace": "active"}), uuid.uuid4(), emit=False
    )

    calm_max = max(len(day.activities) for day in calm.days)
    active_max = max(len(day.activities) for day in active.days)
    assert calm_max <= active_max


@respx.mock
async def test_days_are_balanced_when_places_are_scarce(draft: TripDraft):
    """A short candidate list must not pack day one and starve the rest."""
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)
    counts = [len(day.activities) for day in route.days]

    assert max(counts) - min(counts) <= 1, f"Uneven days: {counts}"


@respx.mock
async def test_no_day_is_a_food_crawl(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    for day in route.days:
        meals = sum(
            1
            for activity in day.activities
            if route.places[activity.place_id].category_kind == "food"
        )
        assert meals <= 2, f"{day.label} has {meals} food stops"


@respx.mock
async def test_activity_times_land_on_five_minute_marks(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    for day in route.days:
        for activity in day.activities:
            minutes = int(activity.time.split(":")[1])
            assert minutes % 5 == 0, f"Ragged start time {activity.time}"


@respx.mock
async def test_transit_modes_are_valid(draft: TripDraft):
    mock_external_apis(respx.mock)

    route = await build_route(draft, uuid.uuid4(), emit=False)

    for day in route.days:
        for leg in day.transits:
            assert leg is not None
            assert leg.mode in {"walk", "taxi", "metro"}
            assert "мин" in leg.label
