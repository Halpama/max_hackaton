"""store adults and children separately

Revision ID: 0005
Revises: 0004
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("adults", sa.Integer(), nullable=True))
    op.add_column("trips", sa.Column("children", sa.Integer(), nullable=True))
    op.execute("UPDATE trips SET adults = travelers, children = 0")
    with op.batch_alter_table("trips") as batch:
        batch.alter_column("adults", nullable=False, server_default="1")
        batch.alter_column("children", nullable=False, server_default="0")


def downgrade() -> None:
    op.drop_column("trips", "children")
    op.drop_column("trips", "adults")