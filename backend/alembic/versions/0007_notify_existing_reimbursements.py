"""Notify admins about existing pending reimbursements."""

import uuid
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_pending_notifs"
down_revision: str | None = "0006_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def format_amount(amount: object) -> str:
    return f"{amount:.2f}".replace(".", ",")


def upgrade() -> None:
    connection = op.get_bind()
    admins = connection.execute(
        sa.text("SELECT id FROM users WHERE role = 'ADMIN'")
    ).scalars().all()
    reimbursements = connection.execute(
        sa.text(
            """
            SELECT movements.id, movements.amount, movements.supplier, users.name
            FROM movements
            JOIN movement_reimbursements
              ON movement_reimbursements.movement_id = movements.id
            JOIN users ON users.id = movements.created_by
            WHERE movement_reimbursements.reimbursed_at IS NULL
            """
        )
    ).mappings().all()
    existing = set(
        connection.execute(
            sa.text(
                """
                SELECT user_id, movement_id
                FROM notifications
                WHERE kind = 'reimbursement_requested'
                """
            )
        ).tuples().all()
    )

    notifications = sa.table(
        "notifications",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("movement_id", sa.Uuid()),
        sa.column("kind", sa.String()),
        sa.column("title", sa.String()),
        sa.column("message", sa.Text()),
    )
    rows = [
        {
            "id": uuid.uuid4(),
            "user_id": admin_id,
            "movement_id": reimbursement["id"],
            "kind": "reimbursement_requested",
            "title": "Rimborso da effettuare",
            "message": (
                f"{reimbursement['name']} attende un rimborso di "
                f"€ {format_amount(reimbursement['amount'])} per {reimbursement['supplier']}."
            ),
        }
        for admin_id in admins
        for reimbursement in reimbursements
        if (admin_id, reimbursement["id"]) not in existing
    ]
    if rows:
        op.bulk_insert(notifications, rows)


def downgrade() -> None:
    pass
