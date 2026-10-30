"""Keep deleted users for history and grant access to existing annual casse."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_user_access_and_deletion"
down_revision: str | None = "0015_audit_reset_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True)))

    # Annual casse created before membership inheritance had only their creator.
    # Fill those active casse from the latest Campo cassa of the same group and unit.
    db = op.get_bind()
    targets = db.execute(sa.text("""
        SELECT c.id, c.group_id, c.unit
        FROM casse c
        JOIN memberships m ON m.cassa_id = c.id
        WHERE c.kind = 'ANNO' AND c.status = 'OPEN'
        GROUP BY c.id, c.group_id, c.unit
        HAVING count(m.id) = 1
    """)).all()
    for target in targets:
        source = db.execute(sa.text("""
            SELECT c.id FROM casse c
            WHERE c.group_id = :group_id AND c.unit = :unit AND c.kind = 'CAMPO'
            ORDER BY (c.status = 'OPEN') DESC, c.year DESC
            LIMIT 1
        """), {"group_id": target.group_id, "unit": target.unit}).scalar()
        if source is None:
            continue
        db.execute(sa.text("""
            INSERT INTO memberships (id, user_id, cassa_id, role)
            SELECT gen_random_uuid(), m.user_id, :target_id, m.role
            FROM memberships m
            JOIN users u ON u.id = m.user_id
            WHERE m.cassa_id = :source_id AND u.is_system_admin = false
            ON CONFLICT (user_id, cassa_id) DO NOTHING
        """), {"target_id": target.id, "source_id": source})


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
