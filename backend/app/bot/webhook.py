from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.bot.client import max_bot
from app.bot.handlers import handle_update
from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/bot", tags=["bot"])


@router.get("/status")
async def bot_status() -> dict[str, object]:
    me: dict | None = None
    error: str | None = None
    if settings.max_bot_enabled and settings.max_bot_token:
        try:
            me = await max_bot.get_me()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    return {
        "enabled": settings.max_bot_enabled,
        "mode": settings.max_bot_mode,
        "tokenConfigured": bool(settings.max_bot_token),
        "webhookUrl": settings.max_bot_webhook_url or None,
        "webhookSecretConfigured": bool(settings.max_bot_webhook_secret),
        "webappUrl": settings.max_webapp_url,
        "me": me,
        "error": error,
    }


@router.post("/webhook")
async def bot_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
) -> JSONResponse:
    """Receive MAX bot updates. Returns 200 even on handler errors."""
    if not settings.max_bot_enabled:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "bot_disabled", "message": "MAX bot is disabled (MAX_BOT_ENABLED=false)"},
        )

    if settings.max_bot_webhook_secret:
        if x_max_bot_api_secret != settings.max_bot_webhook_secret:
            raise UnauthorizedError("Invalid webhook secret")

    update = await request.json()
    # MAX may wrap a single update or send a batch.
    if isinstance(update, dict) and "updates" in update:
        for item in update["updates"]:
            if isinstance(item, dict):
                await handle_update(item)
    elif isinstance(update, dict):
        await handle_update(update)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"ok": True})
