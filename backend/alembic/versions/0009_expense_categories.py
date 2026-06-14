"""Add fixed expense categories and category budgets."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_expense_categories"
down_revision: str | None = "0008_cashier_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "expense_categories",
        sa.Column("slug", sa.String(50), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False, unique=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    categories = sa.table(
        "expense_categories",
        sa.column("slug", sa.String),
        sa.column("label", sa.String),
        sa.column("position", sa.Integer),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        categories,
        [
            {"slug": "vitto", "label": "Vitto", "position": 1, "active": True},
            {"slug": "alloggio", "label": "Alloggio", "position": 2, "active": True},
            {"slug": "trasporti", "label": "Trasporti", "position": 3, "active": True},
            {"slug": "varie", "label": "Varie", "position": 4, "active": True},
        ],
    )
    op.add_column("movements", sa.Column("category", sa.String(50), nullable=True))
    op.create_foreign_key(
        "fk_movements_category_expense_categories",
        "movements",
        "expense_categories",
        ["category"],
        ["slug"],
    )
    op.execute("UPDATE movements SET category = 'varie' WHERE type = 'EXPENSE'")
    op.create_table(
        "camp_category_budgets",
        sa.Column(
            "settings_id",
            sa.Uuid(),
            sa.ForeignKey("camp_settings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category",
            sa.String(50),
            sa.ForeignKey("expense_categories.slug"),
            primary_key=True,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("camp_category_budgets")
    op.drop_constraint("fk_movements_category_expense_categories", "movements", type_="foreignkey")
    op.drop_column("movements", "category")
    op.drop_table("expense_categories")
