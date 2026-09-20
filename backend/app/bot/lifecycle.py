"""Bot lifecycle: webhook registration or long-polling background loop."""
from __future__ import annotations

import asyncio

from app.bot.client import DEFAULT_UPDATE_TYPES, max_bot
from app.bot.handlers import handle_update
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_poll_task: asyncio.Task | None = None


async def start_bot() -> None:
    """Called from FastAPI lifespan when the bot is enabled."""
    if not settings.max_bot_enabled:
        logger.info("MAX bot disabled (MAX_BOT_ENABLED=false)")
        return
    if not settings.max_bot_token:
        logger.warning("MAX_BOT_ENABLED=true but MAX_BOT_TOKEN is empty — bot stays off")
        return

    try:
        me = await max_bot.get_me()
        name = me.get("name") or me.get("username") or me.get("user_id") or "?"
        logger.info("MAX bot online as %s", name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MAX /me failed (%s) — continuing anyway", exc)

    mode = settings.max_bot_mode
    if mode == "off":
        logger.info("MAX bot mode=off — handlers idle until toggled")
        return

    if mode in {"webhook", "auto"} and settings.max_bot_webhook_url:
        await _register_webhook()
        return

    if mode in {"polling", "auto"}:
        await _start_polling()
        return

    logger.warning(
        "MAX bot enabled but neither MAX_BOT_WEBHOOK_URL nor polling is configured "
        "(mode=%s). Webhook endpoint is still live at /api/v1/bot/webhook",
        mode,
    )


async def stop_bot() -> None:
    global _poll_task
    if _poll_task is not None:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
        _poll_task = None
    await max_bot.aclose()


async def _register_webhook() -> None:
    url = settings.max_bot_webhook_url
    assert url
    try:
        await max_bot.set_webhook(
            url,
            secret=settings.max_bot_webhook_secret or None,
            update_types=DEFAULT_UPDATE_TYPES,
        )
        logger.info("MAX webhook registered → %s", url)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to register MAX webhook: %s", exc)


async def _start_polling() -> None:
    global _poll_task
    # Active webhooks block long polling — drop ours if we own the URL.
    try:
        subs = await max_bot.list_subscriptions()
        for sub in subs:
            sub_url = sub.get("url") if isinstance(sub, dict) else None
            if sub_url:
                await max_bot.delete_webhook(sub_url)
                logger.info("Removed MAX webhook %s to enable polling", sub_url)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not clear webhooks before polling: %s", exc)

    _poll_task = asyncio.create_task(_polling_loop(), name="max-bot-polling")
    logger.info("MAX bot long-polling started")


async def _polling_loop() -> None:
    marker: int | None = None
    while True:
        try:
            payload = await max_bot.get_updates(
                marker=marker,
                timeout=25,
                types=DEFAULT_UPDATE_TYPES,
            )
            updates = payload.get("updates") or []
            if payload.get("marker") is not None:
                marker = int(payload["marker"])
            for update in updates:
                if isinstance(update, dict):
                    await handle_update(update)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("MAX polling error: %s — retry in 3s", exc)
            await asyncio.sleep(3)
