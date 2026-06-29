"""Add cassa lifecycle fields."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_cassa_lifecycle"
down_revision: str | None = "0012_system_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

cassa_kind = postgresql.ENUM("CAMPO", "ANNO", name="cassakind")
cassa_status = postgresql.ENUM("OPEN", "CLOSED", name="cassastatus")


def upgrade() -> None:
    bind = op.get_bind()
    cassa_kind.create(bind, checkfirst=True)
    cassa_status.create(bind, checkfirst=True)

    op.add_column("casse", sa.Column("kind", cassa_kind, nullable=True))
    op.add_column("casse", sa.Column("status", cassa_status, nullable=True))
    op.add_column("casse", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("casse", sa.Column("opened_at", sa.Date(), nullable=True))
    op.add_column("casse", sa.Column("closed_at", sa.Date(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE casse c SET "
            "kind = 'CAMPO', "
            "status = 'OPEN', "
            "year = COALESCE((SELECT cs.camp_year FROM camp_settings cs "
            "WHERE cs.cassa_id = c.id ORDER BY cs.created_at DESC LIMIT 1), "
            "EXTRACT(YEAR FROM c.created_at)::int), "
            "opened_at = c.created_at::date"
        )
    )

    op.alter_column("casse", "kind", existing_type=cassa_kind, nullable=False)
    op.alter_column("casse", "status", existing_type=cassa_status, nullable=False)
    op.alter_column("casse", "year", existing_type=sa.Integer(), nullable=False)
    op.alter_column("casse", "opened_at", existing_type=sa.Date(), nullable=False)

    op.drop_constraint("uq_casse_group_unit", "casse", type_="unique")
    op.create_unique_constraint(
        "uq_casse_group_unit_kind_year",
        "casse",
        ["group_id", "unit", "kind", "year"],
    )
    op.create_index(
        "uq_casse_open_group_unit_kind",
        "casse",
        ["group_id", "unit", "kind"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.drop_index("uq_casse_open_group_unit_kind", table_name="casse")
    op.drop_constraint("uq_casse_group_unit_kind_year", "casse", type_="unique")
    op.create_unique_constraint("uq_casse_group_unit", "casse", ["group_id", "unit"])

    op.drop_column("casse", "closed_at")
    op.drop_column("casse", "opened_at")
    op.drop_column("casse", "year")
    op.drop_column("casse", "status")
    op.drop_column("casse", "kind")

    cassa_status.drop(op.get_bind(), checkfirst=True)
    cassa_kind.drop(op.get_bind(), checkfirst=True)
