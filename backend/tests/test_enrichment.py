"""KudaGo, Open-Meteo and openrouteservice — the sources that replace guesswork."""
import uuid
from datetime import date, timedelta

import pytest
import respx

from app.clients.kudago import categories_for, city_slug
from app.clients.osrm import osrm
from app.clients.weather import within_horizon
from app.core.config import settings
from app.schemas.trip import TripDraft
from app.services.pipeline import build_route
from app.services.places import kudago_category, popularity_rating
from tests.fixtures import (
    SAMPLE_DRAFT,
    mock_external_apis,
    mock_kudago,
    mock_ors,
    mock_weather,
)


def test_city_slug_handles_the_names_the_llm_returns():
    assert city_slug("Санкт-Петербург") == "spb"
    assert city_slug("  москва ") == "msk"
    assert city_slug("Суздаль") is None


def test_hotels_are_never_requested():
    """Hotels used to surface as lunch; they are simply not a category we ask for."""
    requested = categories_for(["gastro", "sights", "museums"]).split(",")
    assert "inn" not in requested
    assert "hostels" not in requested
    assert "restaurants" in requested


def test_open_air_places_are_not_priced_as_museums():
    assert kudago_category(["museums"], "Дворцовая площадь") == ("Городская среда", "walk")
    assert kudago_category(["museums"], "Эрмитаж") == ("Музей", "museum")


def test_popularity_rating_spreads_across_the_catalogue():
    """Scoring against the city leader used to squeeze everything into 4.7–5.0."""
    top = popularity_rating(0, 400)
    middle = popularity_rating(200, 400)
    tail = popularity_rating(399, 400)

    assert top == 5.0
    assert tail == 3.9
    assert tail < middle < top
    assert top - middle > 0.4, "the shortlist must not all look identical"


def test_forecast_horizon_rejects_far_future_trips():
    today = date(2026, 5, 1)
    assert within_horizon(date(2026, 5, 10), today=today)
    assert not within_horizon(date(2026, 9, 1), today=today)
    assert not within_horizon(date(2026, 4, 30), today=today)


@pytest.mark.asyncio
@respx.mock
async def test_kudago_supplies_real_ratings_and_opening_hours():
    settings.kudago_enabled = True
    mock_external_apis(respx.mock)
    mock_kudago(respx.mock)

    route = await build_route(TripDraft(**SAMPLE_DRAFT), uuid.uuid4(), emit=False)
    places = list(route.places.values())

    from_catalog = [p for p in places if p.rating_source == "catalog"]
    assert from_catalog, "KudaGo should be the primary source for Saint Petersburg"
    assert any(p.opening_hours for p in from_catalog)
    # The licence requires an indexable link back to the source.
    assert all(p.source_url and p.source_name == "KudaGo" for p in from_catalog)
    assert all("в избранном" in p.reviews_label for p in from_catalog)


@pytest.mark.asyncio
@respx.mock
async def test_guessed_prices_are_flagged_and_free_places_are_not():
    mock_external_apis(respx.mock)

    route = await build_route(TripDraft(**SAMPLE_DRAFT), uuid.uuid4(), emit=False)
    places = list(route.places.values())

    ticketed = [p for p in places if p.price_value]
    free = [p for p in places if p.price_value is None]

    assert ticketed and all(p.price_estimated for p in ticketed)
    # "Бесплатно" for a park is a fact, not an estimate, and must not be hinted.
    assert all(not p.price_estimated for p in free)


@pytest.mark.asyncio
@respx.mock
async def test_weather_lands_on_days_inside_the_horizon():
    settings.weather_enabled = True
    start = date.today() + timedelta(days=2)
    draft = dict(
        SAMPLE_DRAFT,
        startDate=start.isoformat(),
        endDate=(start + timedelta(days=1)).isoformat(),
    )
    mock_external_apis(respx.mock)
    mock_weather(respx.mock, days=[start.isoformat(), (start + timedelta(days=1)).isoformat()])

    route = await build_route(TripDraft(**draft), uuid.uuid4(), emit=False)

    assert any(day.weather for day in route.days)
    forecast = next(day.weather for day in route.days if day.weather)
    assert forecast.icon == "rain"
    assert forecast.temp_high == 14
    assert all(day.date and day.date_label for day in route.days)


@pytest.mark.asyncio
@respx.mock
async def test_far_future_trips_get_no_invented_forecast():
    settings.weather_enabled = True
    start = date.today() + timedelta(days=200)
    draft = dict(
        SAMPLE_DRAFT,
        startDate=start.isoformat(),
        endDate=(start + timedelta(days=1)).isoformat(),
    )
    mock_external_apis(respx.mock)
    # Deliberately no Open-Meteo stub: the client must not call it at all.

    route = await build_route(TripDraft(**draft), uuid.uuid4(), emit=False)

    assert all(day.weather is None for day in route.days)


@pytest.mark.asyncio
@respx.mock
async def test_ors_is_preferred_and_falls_back_when_the_key_is_refused():
    settings.ors_api_key = "test-ors-key"
    settings.ors_min_interval = 0.0
    mock_external_apis(respx.mock)
    mock_ors(respx.mock)

    leg = await osrm.leg((30.31, 59.93), (30.33, 59.94), "foot")
    assert leg["duration"] == 960.0

    osrm._ors_disabled = False
    respx.mock.clear()
    mock_external_apis(respx.mock)
    mock_ors(respx.mock, status=403)

    fallback = await osrm.leg((30.41, 59.83), (30.43, 59.84), "foot")
    assert fallback["duration"] == 720.0, "a refused key must not break the trip"
    osrm._ors_disabled = False
