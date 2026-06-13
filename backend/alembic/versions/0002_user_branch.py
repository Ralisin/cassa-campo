"""Make the user branch mandatory."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_branch"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "default_unit", new_column_name="branch")
    op.execute("UPDATE users SET branch = 'E/G' WHERE branch IS NULL")
    op.alter_column("users", "branch", existing_type=sa.String(50), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "branch", existing_type=sa.String(50), nullable=True)
    op.alter_column("users", "branch", new_column_name="default_unit")
