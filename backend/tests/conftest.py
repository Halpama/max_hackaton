import asyncio
import os
import tempfile

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

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
    # Polling loops in tests would trip the limiter; rate-limit tests opt in.
    settings.rate_limit_enabled = False
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
    # A file DB with NullPool: every session gets its own connection. The
    # in-memory StaticPool shared one SQLite connection between the HTTP
    # request and the background generate_trip task, which raced commits
    # ("cannot commit transaction - SQL statements in progress").
    fd, db_path = tempfile.mkstemp(prefix="trip-test-", suffix=".sqlite3")
    os.close(fd)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_module._engine = engine
    session_module._session_factory = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False
    )

    yield engine

    # Cancel leftover generation tasks so they cannot touch the engine mid-dispose.
    from app.api.v1 import trips as trips_module

    pending = [task for task in trips_module._background_tasks if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    trips_module._background_tasks.clear()
    trips_module._trip_tasks.clear()

    await engine.dispose()
    session_module._engine = None
    session_module._session_factory = None
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
