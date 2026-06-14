"""Add the cashier user role."""

from typing import Sequence

from alembic import op

revision: str = "0008_cashier_role"
down_revision: str | None = "0007_pending_notifs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'CASHIER'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without rebuilding the type.
    pass
