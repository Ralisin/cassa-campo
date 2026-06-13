"""Track completed reimbursements."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_reimbursement_status"
down_revision: str | None = "0002_user_branch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movement_reimbursements", sa.Column("reimbursed_at", sa.DateTime(timezone=True)))
    op.add_column("movement_reimbursements", sa.Column("reimbursed_by", sa.Uuid()))
    op.create_foreign_key(
        "fk_movement_reimbursements_reimbursed_by_users",
        "movement_reimbursements",
        "users",
        ["reimbursed_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_movement_reimbursements_reimbursed_by_users",
        "movement_reimbursements",
        type_="foreignkey",
    )
    op.drop_column("movement_reimbursements", "reimbursed_by")
    op.drop_column("movement_reimbursements", "reimbursed_at")
