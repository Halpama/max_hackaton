import asyncio

import pytest
import respx
from httpx import AsyncClient

from tests.fixtures import SAMPLE_DRAFT, mock_external_apis


async def wait_for_trip(client: AsyncClient, trip_id: str, timeout: float = 20.0) -> dict:
    """Poll until the background generation finishes."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/api/v1/trips/{trip_id}")
        payload = response.json()
        if payload["status"] in {"ready", "failed"}:
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError(f"Trip {trip_id} did not finish in {timeout}s")


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] is True


@respx.mock
async def test_create_and_fetch_trip(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    assert created.status_code == 202
    trip_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    trip = await wait_for_trip(client, trip_id)
    assert trip["status"] == "ready", trip.get("error")
    assert trip["route"]["city"] == "Санкт-Петербург"
    assert trip["draft"]["destination"] == "Санкт-Петербург"
    assert trip["draft"]["startTime"] == "10:00"


@respx.mock
async def test_trip_list_reports_ready_status(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip_id = created.json()["id"]
    await wait_for_trip(client, trip_id)

    listing = await client.get("/api/v1/trips")
    assert listing.status_code == 200
    trips = listing.json()
    assert len(trips) == 1
    assert trips[0]["status"] == "ready"
    assert trips[0]["dateLabel"] == "15–17 сент"
    assert trips[0]["travelersLabel"] == "2 чел"


@respx.mock
async def test_sse_stream_replays_finished_trip(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip_id = created.json()["id"]
    await wait_for_trip(client, trip_id)

    async with client.stream("GET", f"/api/v1/trips/{trip_id}/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = ""
        async for chunk in response.aiter_text():
            body += chunk
            if "event: done" in body:
                break

    assert "event: stage" in body
    assert "event: done" in body
    assert '"key":"analyze"' in body
    assert '"key":"schedule"' in body


@respx.mock
async def test_sse_stream_follows_a_live_generation(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip_id = created.json()["id"]

    stages: list[str] = []
    done = False
    async with client.stream("GET", f"/api/v1/trips/{trip_id}/stream") as response:
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            if "event: done" in buffer:
                done = True
                break

    for key in ("analyze", "places", "transit", "budget", "schedule"):
        if f'"key":"{key}"' in buffer:
            stages.append(key)

    assert done, "Stream ended without a done event"
    assert stages == ["analyze", "places", "transit", "budget", "schedule"]


async def test_unknown_trip_returns_404(client: AsyncClient):
    response = await client.get("/api/v1/trips/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_invalid_draft_is_rejected(client: AsyncClient):
    bad = {**SAMPLE_DRAFT, "travelers": 99}
    response = await client.post("/api/v1/trips", json=bad)
    assert response.status_code == 422


@respx.mock
async def test_places_and_favorites_roundtrip(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip = await wait_for_trip(client, created.json()["id"])
    place_id = next(iter(trip["route"]["places"]))

    place = await client.get(f"/api/v1/places/{place_id}")
    assert place.status_code == 200
    assert place.json()["id"] == place_id
    assert place.json()["categoryKind"] in {"museum", "location", "food", "walk"}

    assert (await client.put(f"/api/v1/favorites/{place_id}")).status_code == 204

    favorites = await client.get("/api/v1/favorites")
    assert [item["id"] for item in favorites.json()] == [place_id]

    assert (await client.delete(f"/api/v1/favorites/{place_id}")).status_code == 204
    assert (await client.get("/api/v1/favorites")).json() == []


@respx.mock
async def test_packing_and_ledger(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip_id = created.json()["id"]
    await wait_for_trip(client, trip_id)

    empty = await client.get(f"/api/v1/trips/{trip_id}/state")
    assert empty.json() == {"packing": []}

    blocks = [
        {"id": "b1", "type": "check", "text": "Паспорт", "done": False},
        {"id": "b2", "type": "bullet", "text": "Зарядка", "done": False},
    ]
    saved = await client.put(f"/api/v1/trips/{trip_id}/state", json={"packing": blocks})
    assert saved.status_code == 200
    assert (await client.get(f"/api/v1/trips/{trip_id}/state")).json()["packing"] == blocks

    entry = await client.post(
        f"/api/v1/trips/{trip_id}/ledger",
        json={"kind": "expense", "amount": 1500, "title": "Обед", "date": "2026-09-15"},
    )
    assert entry.status_code == 201
    assert entry.json()["amount"] == 1500
    assert entry.json()["date"] == "2026-09-15"

    ledger = await client.get(f"/api/v1/trips/{trip_id}/ledger")
    assert len(ledger.json()) == 1

    entry_id = entry.json()["id"]
    assert (await client.delete(f"/api/v1/trips/{trip_id}/ledger/{entry_id}")).status_code == 204
    assert (await client.get(f"/api/v1/trips/{trip_id}/ledger")).json() == []
    missing_entry = await client.delete(f"/api/v1/trips/{trip_id}/ledger/{entry_id}")
    assert missing_entry.status_code == 404


async def test_bot_webhook_is_disabled(client: AsyncClient):
    response = await client.post("/api/v1/bot/webhook", json={"update_type": "message_created"})
    assert response.status_code == 503
    assert response.json()["code"] == "bot_disabled"


@pytest.mark.parametrize("path", ["/api/v1/trips", "/api/v1/favorites"])
async def test_endpoints_work_without_init_data_in_dev_mode(client: AsyncClient, path: str):
    response = await client.get(path)
    assert response.status_code == 200


@respx.mock
async def test_archive_hides_trip_from_list(client: AsyncClient):
    mock_external_apis(respx.mock)

    created = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    trip_id = created.json()["id"]
    await wait_for_trip(client, trip_id)

    deleted = await client.delete(f"/api/v1/trips/{trip_id}")
    assert deleted.status_code == 204

    listing = await client.get("/api/v1/trips")
    assert listing.json() == []

    missing = await client.get(f"/api/v1/trips/{trip_id}")
    assert missing.status_code == 404
