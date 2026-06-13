"""Add movement balance type."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_movement_balance_type"
down_revision: str | None = "0004_treasury_transfers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

balance_type = sa.Enum("ORDINARY", "CAMP", "FUNDRAISING", name="balancetype")


def upgrade() -> None:
    balance_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "movements",
        sa.Column("balance_type", balance_type, server_default="CAMP", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("movements", "balance_type")
    balance_type.drop(op.get_bind(), checkfirst=True)
