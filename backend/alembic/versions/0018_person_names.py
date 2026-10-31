"""Store given name and family name separately for edited users."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_person_names"
down_revision: str | None = "0017_unit_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
