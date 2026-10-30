"""Make existing cash-box memberships consistent within each unit."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_unit_roles"
down_revision: str | None = "0016_user_access_and_deletion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    db = op.get_bind()
    # The strongest existing role wins for a unit, so migration cannot
    # accidentally remove an administrator's access to a historical cassa.
    db.execute(sa.text("""
        WITH unit_roles AS (
            SELECT m.user_id, c.group_id, c.unit,
                CASE max(CASE m.role
                    WHEN 'ADMIN' THEN 3 WHEN 'CASHIER' THEN 2 ELSE 1 END)
                    WHEN 3 THEN 'ADMIN' WHEN 2 THEN 'CASHIER' ELSE 'USER' END::userrole AS role
            FROM memberships m
            JOIN casse c ON c.id = m.cassa_id
            JOIN users u ON u.id = m.user_id
            WHERE u.deleted_at IS NULL
            GROUP BY m.user_id, c.group_id, c.unit
        )
        INSERT INTO memberships (id, user_id, cassa_id, role)
        SELECT gen_random_uuid(), r.user_id, c.id, r.role
        FROM unit_roles r
        JOIN casse c ON c.group_id = r.group_id AND c.unit = r.unit
        ON CONFLICT (user_id, cassa_id) DO UPDATE SET role = EXCLUDED.role
    """))


def downgrade() -> None:
    # Previous per-cassa choices cannot be reconstructed.
    pass
