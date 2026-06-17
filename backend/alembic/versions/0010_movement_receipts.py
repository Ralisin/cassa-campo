"""Add movement receipts."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_movement_receipts"
down_revision: str | None = "0009_expense_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movement_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "movement_id",
            sa.Uuid(),
            sa.ForeignKey("movements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
    )
    op.create_index("ix_movement_receipts_movement_id", "movement_receipts", ["movement_id"])


def downgrade() -> None:
    op.drop_index("ix_movement_receipts_movement_id", table_name="movement_receipts")
    op.drop_table("movement_receipts")
