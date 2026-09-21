import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.core.config import settings

_CONFIGURED = False
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if user_id is not None:
            payload["user_id"] = user_id
        for field in (
            "endpoint",
            "http_method",
            "status_code",
            "response_time_ms",
            "generation_id",
            "stage",
            "event_type",
            "error_type",
            "error_message",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    formatter = JsonFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    log_path = os.getenv("APPLICATION_LOG_PATH", "logs/application.json.log")
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler, file_handler]
    root.setLevel(settings.log_level.upper())

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    return str(uuid.uuid4())


def set_request_context(request_id: str) -> None:
    request_id_var.set(request_id)
    user_id_var.set(None)


def clear_request_context() -> None:
    request_id_var.set(None)
    user_id_var.set(None)


def set_user_context(user_id: int) -> None:
    user_id_var.set(user_id)


def monotonic_seconds() -> float:
    return time.perf_counter()
