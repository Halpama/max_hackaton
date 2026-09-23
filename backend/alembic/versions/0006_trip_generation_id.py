"""track the owner of a background generation

Revision ID: 0006
Revises: 0005
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("generation_id", sa.Uuid(), nullable=True))
    op.create_index("ix_trips_generation_id", "trips", ["generation_id"])


def downgrade() -> None:
    op.drop_index("ix_trips_generation_id", table_name="trips")
    op.drop_column("trips", "generation_id")