"""Update handlers for the MAX trip-planner bot.

The bot is the entry point into the mini-app: welcome, help, and a one-tap
`open_app` button. Heavy UX lives in the SPA — the chat stays short on purpose.
"""
from __future__ import annotations

from app.bot.client import max_bot
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

WELCOME = (
    "Привет! Я **Trip Planner** — соберу маршрут поездки по дням.\n\n"
    "Укажи город, даты и интересы в мини-приложении — "
    "ИИ подберёт места, время в пути и бюджет."
)

HELP = (
    "**Что умею**\n"
    "• Собрать маршрут на 1–несколько дней\n"
    "• Учесть интересы, темп и бюджет\n"
    "• Показать погоду и часы работы мест\n\n"
    "**Команды**\n"
    "/start — открыть планировщик\n"
    "/help — эта справка\n"
    "/about — про проект\n\n"
    "Нажми кнопку ниже или напиши город в мини-приложении."
)

ABOUT = (
    "**Trip Planner** — мини-приложение для хакатона MAX.\n"
    "Стек: FastAPI · Postgres · Redis · GigaChat · KudaGo · OpenTripMap.\n\n"
    f"Веб-версия: {settings.max_webapp_url}"
)

HELP_TRIGGERS = {"/help", "помощь", "help", "?"}
ABOUT_TRIGGERS = {"/about", "о боте", "about"}
START_TRIGGERS = {"/start", "start", "начать", "старт"}


def extract_chat_id(update: dict) -> int | None:
    """Best-effort chat id across bot_started / message / callback shapes."""
    for key in ("chat_id", "chatId"):
        if update.get(key) is not None:
            return int(update[key])

    chat = update.get("chat") or {}
    if chat.get("chat_id") is not None:
        return int(chat["chat_id"])

    message = update.get("message") or {}
    recipient = message.get("recipient") or {}
    if recipient.get("chat_id") is not None:
        return int(recipient["chat_id"])

    # Private dialogs sometimes only carry the user id.
    for container in (message.get("sender") or {}, update.get("user") or {}):
        if container.get("user_id") is not None:
            return None  # signal callers to use user_id instead

    callback = update.get("callback") or {}
    message = callback.get("message") or message
    recipient = message.get("recipient") or {}
    if recipient.get("chat_id") is not None:
        return int(recipient["chat_id"])

    return None


def extract_user_id(update: dict) -> int | None:
    message = update.get("message") or {}
    sender = message.get("sender") or {}
    if sender.get("user_id") is not None:
        return int(sender["user_id"])

    user = update.get("user") or {}
    if user.get("user_id") is not None:
        return int(user["user_id"])

    callback = update.get("callback") or {}
    cb_user = callback.get("user") or {}
    if cb_user.get("user_id") is not None:
        return int(cb_user["user_id"])

    return None


def extract_text(update: dict) -> str:
    body = (update.get("message") or {}).get("body") or {}
    text = body.get("text")
    if text:
        return str(text).strip()

    callback = update.get("callback") or {}
    payload = callback.get("payload")
    if payload:
        return str(payload).strip()

    return ""


async def _reply(update: dict, text: str, *, with_keyboard: bool = True) -> None:
    chat_id = extract_chat_id(update)
    user_id = extract_user_id(update)
    if chat_id is None and user_id is None:
        logger.warning("MAX update without chat_id/user_id: %s", update.get("update_type"))
        return

    if with_keyboard:
        await max_bot.send_planner_invite(chat_id=chat_id, user_id=user_id, text=text)
    else:
        await max_bot.send_message(chat_id=chat_id, user_id=user_id, text=text)


async def handle_update(update: dict) -> None:
    """Dispatch one MAX update. Never raises — a webhook must always answer 200."""
    update_type = update.get("update_type") or update.get("type") or "unknown"
    chat_id = extract_chat_id(update)
    user_id = extract_user_id(update)
    logger.info("MAX update %s chat=%s user=%s", update_type, chat_id, user_id)

    if not settings.max_bot_enabled:
        return
    if chat_id is None and user_id is None:
        return

    try:
        if update_type in {"bot_started", "bot_added"}:
            await _reply(update, WELCOME)
            return

        if update_type == "message_callback":
            payload = str((update.get("callback") or {}).get("payload") or "").strip().lower()
            if payload in HELP_TRIGGERS or payload == "/help":
                await _reply(update, HELP)
            elif payload in ABOUT_TRIGGERS:
                await _reply(update, ABOUT, with_keyboard=False)
            else:
                await _reply(update, WELCOME)
            return

        if update_type == "message_created":
            text = extract_text(update).lower()
            # Strip bot mention prefixes like "@trip_bot /start".
            if " " in text and text.startswith("@"):
                text = text.split(" ", 1)[-1].strip()

            if not text or any(text.startswith(t) for t in START_TRIGGERS) or text in START_TRIGGERS:
                await _reply(update, WELCOME)
            elif text in HELP_TRIGGERS or text.startswith("/help"):
                await _reply(update, HELP)
            elif text in ABOUT_TRIGGERS or text.startswith("/about"):
                await _reply(update, ABOUT, with_keyboard=False)
            else:
                await _reply(
                    update,
                    "Маршрут собирается в мини-приложении — там удобнее указать "
                    "город, даты и интересы.\n\nНажми кнопку ниже 👇",
                )
            return

        logger.debug("Ignoring MAX update_type=%s", update_type)
    except Exception as exc:  # noqa: BLE001 - never fail the webhook
        logger.exception("Failed to handle MAX update: %s", exc)
