import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB on Postgres, plain JSON on SQLite so tests can run without a server.
JsonColumn = JSONB().with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))

    trips: Mapped[list["Trip"]] = relationship(back_populates="user")


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    destination: Mapped[str] = mapped_column(String(256))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    budget: Mapped[int] = mapped_column(Integer, default=0)
    travelers: Mapped[int] = mapped_column(Integer, default=1)
    interests: Mapped[list[str]] = mapped_column(JsonColumn, default=list)
    pace: Mapped[str] = mapped_column(String(16), default="medium")
    find_housing: Mapped[bool] = mapped_column(default=False)

    # pending | running | ready | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    stage: Mapped[str | None] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)
    route_plan: Mapped[dict | None] = mapped_column(JsonColumn)
    #: Soft-hide from the home list; row and caches stay intact.
    archived: Mapped[bool] = mapped_column(default=False, index=True)

    user: Mapped[User] = relationship(back_populates="trips")
    state: Mapped["TripState | None"] = relationship(
        back_populates="trip", cascade="all, delete-orphan", uselist=False
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )


class Place(Base, TimestampMixin):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # OpenTripMap xid, or a synthetic slug for places we invent (meals, walks).
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    city: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict] = mapped_column(JsonColumn)


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    place_external_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TripState(Base, TimestampMixin):
    """Packing checklist blocks, mirroring the frontend block editor."""

    __tablename__ = "trip_state"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )
    packing: Mapped[list] = mapped_column(JsonColumn, default=list)

    trip: Mapped[Trip] = relationship(back_populates="state")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), index=True
    )
    # expense | topup
    kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(256))
    entry_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip: Mapped[Trip] = relationship(back_populates="ledger_entries")


Index("ix_ledger_trip_date", LedgerEntry.trip_id, LedgerEntry.entry_date)
