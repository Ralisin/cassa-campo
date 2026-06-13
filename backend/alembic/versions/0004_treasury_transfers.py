"""Add treasury transfers."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_treasury_transfers"
down_revision: str | None = "0003_reimbursement_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transfer_type = sa.Enum("WITHDRAWAL", "DEPOSIT", name="transfertype")


def upgrade() -> None:
    op.create_table(
        "treasury_transfers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("type", transfer_type, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("treasury_transfers")
    transfer_type.drop(op.get_bind())
