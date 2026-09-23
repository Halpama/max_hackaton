import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.cache.redis import set_redis
from app.core.config import settings
from app.db import session as session_module
from app.db.models import Base


@pytest.fixture(autouse=True)
def dev_auth():
    """Tests run in dev auth mode with GigaChat off, so LLM fallbacks are exercised."""
    settings.auth_mode = "dev"
    settings.dev_user_id = 1
    settings.gigachat_auth_key = ""
    settings.opentripmap_api_key = "test-key"
    settings.opentripmap_min_interval = 0.0
    # Enrichment sources are opt-in per test so the OpenTripMap path stays
    # deterministic; the tests that care switch them back on.
    settings.kudago_enabled = False
    settings.weather_enabled = False
    settings.ors_api_key = ""
    # A developer .env may enable the bot; webhook tests must stay deterministic.
    settings.max_bot_enabled = False
    yield


@pytest_asyncio.fixture(autouse=True)
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    set_redis(client)
    yield client
    await client.aclose()
    set_redis(None)


@pytest_asyncio.fixture(autouse=True)
async def database():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_module._engine = engine
    session_module._session_factory = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False
    )

    yield engine

    await engine.dispose()
    session_module._engine = None
    session_module._session_factory = None


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
