from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for errors that map to a predictable HTTP response."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str, *, details: object | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class UpstreamError(AppError):
    """An external provider (GigaChat / OpenTripMap / OSRM) failed."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


class QuotaExceededError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "quota_exceeded"


class ConfigurationError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "not_configured"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "internal_error", "message": "Internal server error"},
        )
