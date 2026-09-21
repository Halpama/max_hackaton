import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_var, user_id_var
from app.db.models import AuditEvent
from app.db.session import get_session_factory


async def record_event(
    event_type: str,
    *,
    user_id: int | None = None,
    trip_id: uuid.UUID | None = None,
    generation_id: uuid.UUID | None = None,
    stage: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    error: Exception | None = None,
    payload: dict[str, Any] | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Persist a safe business/audit event without allowing audit failure to break work."""
    event = AuditEvent(
        event_type=event_type,
        user_id=user_id if user_id is not None else user_id_var.get(),
        trip_id=trip_id,
        generation_id=generation_id,
        request_id=request_id_var.get(),
        stage=stage,
        status=status,
        duration_ms=duration_ms,
        error_type=type(error).__name__ if error else None,
        error_message=str(error) if error else None,
        payload=payload,
    )
    if session is not None:
        session.add(event)
        await session.flush()
        return

    try:
        async with get_session_factory()() as session:
            session.add(event)
            await session.commit()
    except Exception:
        # Observability must never turn a successful user operation into a failure.
        return