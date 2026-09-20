"""trip soft archive flag

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_trips_archived", "trips", ["archived"])


def downgrade() -> None:
    op.drop_index("ix_trips_archived", table_name="trips")
    op.drop_column("trips", "archived")
