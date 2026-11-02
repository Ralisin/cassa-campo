"""Track annual dues on income movements and add bank transfer method."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_annual_dues"
down_revision: str | None = "0019_movement_performer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'BANK'")
    op.add_column("movements", sa.Column("annual_dues_person", sa.String(255), nullable=True))
    op.add_column("movements", sa.Column("annual_dues_person_key", sa.String(255), nullable=True))
    op.add_column("camp_settings", sa.Column("annual_balances_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index(
        "uq_movements_active_annual_dues_person", "movements",
        ["cassa_id", "annual_dues_person_key"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_movements_active_annual_dues_person", table_name="movements")
    op.drop_column("movements", "annual_dues_person_key")
    op.drop_column("movements", "annual_dues_person")
    op.drop_column("camp_settings", "annual_balances_confirmed")
    # PostgreSQL enum values are deliberately retained on downgrade.
