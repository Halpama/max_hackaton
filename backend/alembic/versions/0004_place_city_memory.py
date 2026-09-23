"""persist place/city memory that survives Redis flush

Revision ID: 0004
Revises: 0003
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "place_stats",
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("category_kind", sa.String(length=32), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("pick_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stay_minutes_sum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stay_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_name", sa.String(length=64), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column("tip", sa.Text(), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("external_id"),
    )
    op.create_index("ix_place_stats_city", "place_stats", ["city"])

    op.create_table(
        "city_memory",
        sa.Column("city_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("radius_meters", sa.Integer(), nullable=True),
        sa.Column("trip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discovery_hints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("digest", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("city_key"),
    )


def downgrade() -> None:
    op.drop_table("city_memory")
    op.drop_index("ix_place_stats_city", table_name="place_stats")
    op.drop_table("place_stats")
