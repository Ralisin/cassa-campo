"""Record who made a purchase separately from who entered it."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_movement_performer"
down_revision: str | None = "0018_person_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movements", sa.Column("performed_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_movements_performed_by_id_users", "movements", "users", ["performed_by_id"], ["id"]
    )
    op.execute("UPDATE movements SET performed_by_id = created_by")


def downgrade() -> None:
    op.drop_constraint("fk_movements_performed_by_id_users", "movements", type_="foreignkey")
    op.drop_column("movements", "performed_by_id")
