from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.bot.client import max_bot
from app.bot.handlers import WELCOME, handle_update
from app.core.config import settings
from app.core.errors import ConfigurationError, UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/bot", tags=["bot"])


class InviteRequest(BaseModel):
    """Dev helper: push a planner invite to a known MAX user / chat."""

    user_id: int | None = Field(default=None, alias="userId")
    chat_id: int | None = Field(default=None, alias="chatId")
    text: str | None = None

    model_config = {"populate_by_name": True}


def _resolved_mode() -> str:
    mode = settings.max_bot_mode
    if mode == "off":
        return "off"
    if mode in {"webhook", "auto"} and settings.max_bot_webhook_url:
        return "webhook"
    if mode in {"polling", "auto"}:
        return "polling"
    return mode


@router.get("/status")
async def bot_status() -> dict[str, object]:
    me: dict | None = None
    error: str | None = None
    keyboard: list | None = None
    if settings.max_bot_enabled and settings.max_bot_token:
        try:
            me = await max_bot.get_me()
            keyboard = max_bot.planner_keyboard()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    return {
        "enabled": settings.max_bot_enabled,
        "mode": settings.max_bot_mode,
        "resolvedMode": _resolved_mode(),
        "tokenConfigured": bool(settings.max_bot_token),
        "webhookUrl": settings.max_bot_webhook_url or None,
        "webhookSecretConfigured": bool(settings.max_bot_webhook_secret),
        "webappUrl": settings.max_webapp_url,
        "deeplink": max_bot.max_deeplink() if me else None,
        "openApp": (keyboard[0][0] if keyboard else None),
        "me": {
            "userId": max_bot.bot_user_id,
            "username": max_bot.bot_username,
            "name": (me or {}).get("name") or (me or {}).get("first_name"),
            "isBot": (me or {}).get("is_bot"),
        }
        if me
        else None,
        "error": error,
    }


@router.post("/invite")
async def bot_invite(body: InviteRequest) -> dict[str, object]:
    """Send the /start keyboard to a user. Useful to verify open_app without chat."""
    if not settings.max_bot_enabled:
        raise ConfigurationError("MAX bot is disabled (MAX_BOT_ENABLED=false)")
    if body.user_id is None and body.chat_id is None:
        raise ConfigurationError("userId or chatId is required")

    text = body.text or WELCOME
    result = await max_bot.send_planner_invite(
        chat_id=body.chat_id,
        user_id=body.user_id,
        text=text,
    )
    return {"ok": True, "message": result, "openApp": max_bot.planner_keyboard()[0][0]}


@router.post("/webhook")
async def bot_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
) -> JSONResponse:
    """Receive MAX bot updates. Returns 200 even on handler errors."""
    if not settings.max_bot_enabled:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "bot_disabled",
                "message": "MAX bot is disabled (MAX_BOT_ENABLED=false)",
            },
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
