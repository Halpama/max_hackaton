from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.bot.lifecycle import start_bot, stop_bot
from app.cache.redis import close_redis, get_redis
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, setup_logging
from app.db.session import dispose_engine

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Starting Trip Planner (env=%s, auth=%s, bot=%s/%s)",
        settings.app_env,
        settings.auth_mode,
        "on" if settings.max_bot_enabled else "off",
        settings.max_bot_mode,
    )
    if not settings.gigachat_configured:
        logger.warning("GIGACHAT_AUTH_KEY is empty — LLM stages will use fallbacks")
    if not settings.opentripmap_configured:
        logger.warning("OPENTRIPMAP_API_KEY is empty — place search will fail outside KudaGo cities")

    await start_bot()
    yield
    await stop_bot()
    await close_redis()
    await dispose_engine()
    logger.info("Trip Planner backend stopped")


app = FastAPI(
    title="Trip Planner API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    # Dev: phone / LAN Vite origins (http://192.168.x.x:5173) without listing every IP.
    allow_origin_regex=r"https?://.*" if settings.app_env == "development" else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, object]:
    """Liveness probe plus a quick view of which integrations are configured."""
    redis_ok = True
    try:
        await (await get_redis()).ping()
    except Exception:  # noqa: BLE001 - health must never raise
        redis_ok = False

    return {
        "status": "ok" if redis_ok else "degraded",
        "env": settings.app_env,
        "redis": redis_ok,
        "gigachat": settings.gigachat_configured,
        "opentripmap": settings.opentripmap_configured,
        "ors": settings.ors_configured,
        "kudago": settings.kudago_enabled,
        "weather": settings.weather_enabled,
        "bot": {
            "enabled": settings.max_bot_enabled,
            "configured": settings.max_bot_configured,
            "mode": settings.max_bot_mode,
            "webhookUrl": settings.max_bot_webhook_url or None,
        },
    }
