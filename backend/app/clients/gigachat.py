import ssl
import time
import uuid

import httpx
import orjson

from app.cache import keys
from app.cache.decorator import cached_json
from app.cache.redis import get_redis
from app.core.config import settings
from app.core.errors import ConfigurationError, UpstreamError
from app.core.logging import get_logger

logger = get_logger(__name__)

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

_TOKEN_SKEW_SECONDS = 60


def _ssl_context() -> ssl.SSLContext | bool:
    if not settings.gigachat_verify_ssl:
        return False
    # The Russian Trusted Root CA is added to the system store in the Dockerfile.
    return ssl.create_default_context()


class GigaChatClient:
    """Thin GigaChat wrapper: cached OAuth token, cached JSON completions."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                verify=_ssl_context(),
                timeout=httpx.Timeout(90.0, connect=15.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _fetch_token(self) -> tuple[str, int]:
        client = await self._http()
        response = await client.post(
            OAUTH_URL,
            headers={
                "Authorization": f"Basic {settings.gigachat_auth_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": settings.gigachat_scope},
        )
        if response.status_code != 200:
            raise UpstreamError(
                f"GigaChat OAuth failed: {response.status_code} {response.text[:200]}"
            )

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise UpstreamError("GigaChat OAuth returned no access_token")

        # expires_at comes back as epoch milliseconds.
        expires_at_ms = int(payload.get("expires_at", 0))
        ttl = int(expires_at_ms / 1000 - time.time()) - _TOKEN_SKEW_SECONDS
        return token, max(ttl, 60)

    async def _token(self) -> str:
        if not settings.gigachat_configured:
            raise ConfigurationError("GIGACHAT_AUTH_KEY is not set")

        try:
            redis = await get_redis()
            cached = await redis.get(keys.gigachat_token())
            if cached:
                return cached
        except Exception as exc:  # noqa: BLE001 - fall back to a fresh token
            logger.warning("Could not read cached GigaChat token: %s", exc)
            redis = None

        token, ttl = await self._fetch_token()

        try:
            redis = await get_redis()
            await redis.set(keys.gigachat_token(), token, ex=ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not cache GigaChat token: %s", exc)

        return token

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        json_response: bool = True,
    ) -> str:
        """Run a chat completion, caching identical prompts for a day."""
        body: dict[str, object] = {
            "model": settings.gigachat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_response:
            body["function_call"] = "none"

        cache_key = keys.gigachat_completion(settings.gigachat_model, orjson.dumps(body))

        async def produce() -> str:
            token = await self._token()
            client = await self._http()
            response = await client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
            if response.status_code == 401:
                # Token expired early — drop it and retry once with a fresh one.
                try:
                    redis = await get_redis()
                    await redis.delete(keys.gigachat_token())
                except Exception:  # noqa: BLE001
                    pass
                token = await self._token()
                response = await client.post(
                    API_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=body,
                )

            if response.status_code != 200:
                raise UpstreamError(
                    f"GigaChat completion failed: {response.status_code} {response.text[:300]}"
                )

            payload = response.json()
            choices = payload.get("choices") or []
            if not choices:
                raise UpstreamError("GigaChat returned no choices")
            return choices[0].get("message", {}).get("content", "")

        return await cached_json(cache_key, keys.TTL_COMPLETION, produce)


gigachat = GigaChatClient()
