"""Add hidden system administrator flag."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_system_admin"
down_revision: str | None = "0011_multitenant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_system_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_system_admin")
