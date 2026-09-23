from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.api.v1.trips import resume_pending_trips
from app.bot.lifecycle import start_bot, stop_bot
from app.cache.redis import close_redis, get_redis
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import (
    clear_request_context,
    get_logger,
    monotonic_seconds,
    new_request_id,
    set_request_context,
    setup_logging,
)
from app.core.rate_limit import RATE_LIMIT_CODE, allow_request
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
    await resume_pending_trips()
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


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    set_request_context(request_id)
    request.state.request_id = request_id
    started = monotonic_seconds()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.exception(
            "Unhandled request exception",
            extra={
                "endpoint": request.url.path,
                "http_method": request.method,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise
    finally:
        logger.info(
            "HTTP request completed",
            extra={
                "endpoint": request.url.path,
                "http_method": request.method,
                "status_code": response.status_code if response is not None else 500,
                "response_time_ms": round((monotonic_seconds() - started) * 1000, 2),
            },
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        clear_request_context()

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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # CORS preflights carry no credentials and must never be throttled.
    if request.method != "OPTIONS" and not await allow_request(
        request.method,
        request.url.path,
        request.headers.get("Authorization"),
        request.client.host if request.client else None,
    ):
        return JSONResponse(
            status_code=429,
            content={
                "code": RATE_LIMIT_CODE,
                "message": "Слишком много запросов. Попробуйте позже.",
            },
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )
    return await call_next(request)

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
