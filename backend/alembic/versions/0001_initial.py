"""Initial schema."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("ADMIN", "USER", name="userrole")
movement_type = sa.Enum("INCOME", "EXPENSE", name="movementtype")
payment_method = sa.Enum("CASH", "CARD", name="paymentmethod")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("default_unit", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "camp_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("camp_year", sa.Integer(), nullable=False),
        sa.Column("camp_name", sa.String(255), nullable=False),
        sa.Column("participants", sa.Integer(), nullable=False),
        sa.Column("quota_per_person", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_budget", sa.Numeric(10, 2), nullable=False),
        sa.Column("cash_initial", sa.Numeric(10, 2), nullable=False),
        sa.Column("bank_initial", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("type", movement_type, nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("supplier", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_table(
        "movement_reimbursements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "movement_id",
            sa.Uuid(),
            sa.ForeignKey("movements.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("movement_reimbursements")
    op.drop_table("movements")
    op.drop_table("camp_settings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    payment_method.drop(op.get_bind())
    movement_type.drop(op.get_bind())
    user_role.drop(op.get_bind())

