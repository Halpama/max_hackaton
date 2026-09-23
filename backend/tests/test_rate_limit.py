"""Rate limiter contract: budgets per bucket, exemptions, fail-open behaviour."""
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.fixtures import SAMPLE_DRAFT


@pytest.fixture
def rate_limit_on(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    return settings


async def test_trip_post_limited(client: AsyncClient, rate_limit_on, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_trip_max", 2)

    for _ in range(2):
        response = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
        assert response.status_code == 202

    blocked = await client.post("/api/v1/trips", json=SAMPLE_DRAFT)
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "rate_limited"
    assert blocked.headers.get("Retry-After") == str(settings.rate_limit_window_seconds)


async def test_global_budget_applies_to_ordinary_endpoints(
    client: AsyncClient, rate_limit_on, monkeypatch
):
    monkeypatch.setattr(settings, "rate_limit_max_requests", 3)

    for _ in range(3):
        assert (await client.get("/api/v1/favorites")).status_code == 200

    blocked = await client.get("/api/v1/favorites")
    assert blocked.status_code == 429


async def test_bot_webhook_is_exempt(client: AsyncClient, rate_limit_on, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)

    assert (await client.get("/api/v1/favorites")).status_code == 200
    assert (await client.get("/api/v1/favorites")).status_code == 429

    # The MAX platform hits the webhook from shared egress IPs — never throttled.
    webhook = await client.post(
        "/api/v1/bot/webhook", json={"update_type": "message_created"}
    )
    assert webhook.status_code == 503  # bot disabled, not rate limited
    assert webhook.json()["code"] == "bot_disabled"


async def test_health_is_exempt(client: AsyncClient, rate_limit_on, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)

    assert (await client.get("/api/v1/favorites")).status_code == 200
    assert (await client.get("/health")).status_code == 200


async def test_disabled_flag_removes_limits(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)

    for _ in range(3):
        assert (await client.get("/api/v1/favorites")).status_code == 200


async def test_redis_outage_fails_open(client: AsyncClient, rate_limit_on, monkeypatch):
    async def broken():
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.core.rate_limit.get_redis", broken)
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)

    for _ in range(3):
        assert (await client.get("/api/v1/favorites")).status_code == 200


async def test_geo_bucket_is_stricter(client: AsyncClient, rate_limit_on, monkeypatch):
    async def no_suggestions(q: str, limit: int = 8):
        return []

    monkeypatch.setattr("app.clients.geocoding.suggest_cities", no_suggestions)
    monkeypatch.setattr(settings, "rate_limit_geo_max", 1)

    first = await client.get("/api/v1/geo/cities", params={"q": "Мос"})
    assert first.status_code == 200

    blocked = await client.get("/api/v1/geo/cities", params={"q": "Мос"})
    assert blocked.status_code == 429
