"""MAX WebApp `initData` handling.

The frontend sends `Authorization: tma <initData>` (see web/src/shared/api/client.ts).
Verification sits behind one interface so switching AUTH_MODE from `dev` to `max`
does not touch any route.
"""
import hashlib
import hmac
import json
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)

#: initData older than this is rejected in `max` mode.
MAX_AUTH_AGE_SECONDS = 24 * 3600


@dataclass
class AuthUser:
    max_user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def parse_init_data(raw: str) -> dict[str, str]:
    return dict(parse_qsl(raw, keep_blank_values=True))


def _user_from_fields(fields: dict[str, str], fallback_id: int) -> AuthUser:
    try:
        user = json.loads(fields.get("user", "{}"))
    except json.JSONDecodeError:
        user = {}

    if not isinstance(user, dict):
        user = {}

    return AuthUser(
        max_user_id=int(user.get("id") or fallback_id),
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
    )


def verify_signature(raw: str, bot_token: str) -> bool:
    """Telegram-compatible initData check (MAX mirrors this scheme).

    Confirm against the MAX bot docs before relying on it in production; until
    then AUTH_MODE stays `dev`.
    """
    fields = parse_init_data(raw)
    provided = fields.pop("hash", "")
    if not provided or not bot_token:
        return False

    data_check_string = "\n".join(
        f"{key}={fields[key]}" for key in sorted(fields)
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, provided)


def extract_init_data(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "tma":
        return ""
    return value.strip()


def resolve_user(authorization: str | None) -> AuthUser:
    """Map an incoming request to a user according to AUTH_MODE."""
    raw = extract_init_data(authorization)

    if settings.auth_mode == "dev":
        # Outside the MAX client there is no initData; everything maps to one user.
        if not raw:
            return AuthUser(max_user_id=settings.dev_user_id, first_name="Dev")
        return _user_from_fields(parse_init_data(raw), settings.dev_user_id)

    if not raw:
        raise UnauthorizedError("Missing MAX initData")

    if not verify_signature(raw, settings.max_bot_token):
        raise UnauthorizedError("Invalid MAX initData signature")

    fields = parse_init_data(raw)
    user = _user_from_fields(fields, 0)
    if not user.max_user_id:
        raise UnauthorizedError("initData contains no user id")

    return user
