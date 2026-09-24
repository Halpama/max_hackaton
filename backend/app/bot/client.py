"""MAX Bot API client — platform-api2.max.ru with Authorization header.

Auth used to be `?access_token=`; that is retired. The current contract is the
`Authorization` header and the `platform-api2.max.ru` host (see
https://dev.max.ru/docs-api).
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.errors import ConfigurationError, UpstreamError
from app.core.logging import get_logger
from app.core.ssl_ru import russian_trusted_ssl_context

logger = get_logger(__name__)

BASE_URL = "https://platform-api2.max.ru"

#: Events we care about for the trip-planner bot.
DEFAULT_UPDATE_TYPES = [
    "message_created",
    "bot_started",
    "bot_added",
    "message_callback",
]


class MaxBotClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._me: dict | None = None

    async def _http(self) -> httpx.AsyncClient:
        if not settings.max_bot_token:
            raise ConfigurationError("MAX_BOT_TOKEN is not set")
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=httpx.Timeout(30.0, connect=10.0),
                verify=russian_trusted_ssl_context(),
                headers={
                    "Authorization": settings.max_bot_token,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._me = None

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        client = await self._http()
        response = await client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise UpstreamError(
                f"MAX Bot API {path} failed: {response.status_code} {response.text[:240]}"
            )
        if not response.content:
            return {}
        return response.json()

    async def get_me(self, *, force: bool = False) -> dict:
        if self._me is not None and not force:
            return self._me
        data = await self._request("GET", "/me")
        self._me = data if isinstance(data, dict) else {}
        return self._me

    @property
    def bot_user_id(self) -> int | None:
        if not self._me:
            return None
        raw = self._me.get("user_id")
        if raw is None:
            raw = self._me.get("userId")
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def bot_username(self) -> str | None:
        if not self._me:
            return None
        name = self._me.get("username")
        return str(name).lstrip("@") if name else None

    def max_deeplink(self, *, startapp: bool = True) -> str | None:
        """In-MAX link that opens the mini-app bound to this bot in the cabinet."""
        username = self.bot_username
        if not username:
            return None
        base = f"https://max.ru/{username}"
        return f"{base}?startapp" if startapp else base

    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: str,
        attachments: list | None = None,
        format: str | None = "markdown",
    ) -> dict:
        if chat_id is None and user_id is None:
            raise ValueError("chat_id or user_id is required")

        params: dict[str, int] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None:
            params["user_id"] = user_id

        body: dict[str, object] = {"text": text}
        if attachments:
            body["attachments"] = attachments
        if format:
            body["format"] = format

        data = await self._request("POST", "/messages", params=params, json=body)
        return data if isinstance(data, dict) else {}

    def planner_keyboard(self) -> list:
        """Inline keyboard: native `open_app` only.

        The mini-app opens exclusively through the platform `open_app` control
        (SPA URL is bound in the MAX cabinet, not in the button). Browser /
        deeplink rows would duplicate that path and are intentionally omitted.
        Utility callbacks (help / about) stay in chat and do not open the app.
        """
        open_app: dict[str, object] = {
            "type": "open_app",
            "text": "Открыть планировщик",
            "payload": "planner",
        }
        if self.bot_username:
            open_app["web_app"] = self.bot_username
        if self.bot_user_id is not None:
            open_app["contact_id"] = self.bot_user_id

        return [
            [open_app],
            [
                {"type": "callback", "text": "Помощь", "payload": "/help"},
                {"type": "callback", "text": "О боте", "payload": "/about"},
            ],
        ]

    async def send_planner_invite(
        self, *, chat_id: int | None = None, user_id: int | None = None, text: str
    ) -> dict:
        # Need /me so open_app carries contact_id / username.
        try:
            await self.get_me()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not refresh MAX /me before invite: %s", exc)

        attachments = [
            {
                "type": "inline_keyboard",
                "payload": {"buttons": self.planner_keyboard()},
            }
        ]
        return await self.send_message(
            chat_id=chat_id, user_id=user_id, text=text, attachments=attachments
        )

    async def set_webhook(
        self,
        url: str,
        *,
        secret: str | None = None,
        update_types: list[str] | None = None,
    ) -> dict:
        body: dict[str, object] = {
            "url": url,
            "update_types": update_types or DEFAULT_UPDATE_TYPES,
        }
        if secret:
            body["secret"] = secret
        data = await self._request("POST", "/subscriptions", json=body)
        return data if isinstance(data, dict) else {}

    async def list_subscriptions(self) -> list:
        data = await self._request("GET", "/subscriptions")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.get("subscriptions") or data.get("result") or [])
        return []

    async def delete_webhook(self, url: str | None = None) -> dict:
        params = {"url": url} if url else None
        data = await self._request("DELETE", "/subscriptions", params=params)
        return data if isinstance(data, dict) else {}

    async def get_updates(
        self,
        *,
        marker: int | None = None,
        timeout: int = 25,
        types: list[str] | None = None,
        limit: int = 100,
    ) -> dict:
        """Long polling. Mutually exclusive with an active webhook subscription."""
        params: dict[str, object] = {"timeout": timeout, "limit": limit}
        if marker is not None:
            params["marker"] = marker
        if types:
            params["types"] = ",".join(types)
        data = await self._request("GET", "/updates", params=params)
        return data if isinstance(data, dict) else {}


max_bot = MaxBotClient()
