"""Multi-tenant: groups, casse per unit, memberships and cassa scoping."""

import uuid as uuidlib
from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_multitenant"
down_revision: str | None = "0010_movement_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Reuse the existing Postgres enum type instead of recreating it.
userrole = postgresql.ENUM("ADMIN", "USER", "CASHIER", name="userrole", create_type=False)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. New tenant tables ----------------------------------------------------
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email_domain", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_groups_slug", "groups", ["slug"])
    op.create_index("ix_groups_email_domain", "groups", ["email_domain"])

    op.create_table(
        "casse",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Uuid(),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "unit", name="uq_casse_group_unit"),
    )
    op.create_index("ix_casse_group_id", "casse", ["group_id"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cassa_id",
            sa.Uuid(),
            sa.ForeignKey("casse.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", userrole, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "cassa_id", name="uq_memberships_user_cassa"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_cassa_id", "memberships", ["cassa_id"])

    # 2. Nullable scope columns (filled below, then made NOT NULL) -------------
    op.add_column("users", sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=True))
    op.add_column(
        "movements",
        sa.Column("cassa_id", sa.Uuid(), sa.ForeignKey("casse.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "treasury_transfers",
        sa.Column("cassa_id", sa.Uuid(), sa.ForeignKey("casse.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "camp_settings",
        sa.Column("cassa_id", sa.Uuid(), sa.ForeignKey("casse.id", ondelete="CASCADE"), nullable=True),
    )

    # 3. Data migration -------------------------------------------------------
    users = conn.execute(sa.text("SELECT id, email, role, branch FROM users")).all()

    # 3a. One group per email domain.
    domain_to_group: dict[str, uuidlib.UUID] = {}
    used_slugs: set[str] = set()
    for user in users:
        domain = user.email.split("@")[1].lower()
        if domain in domain_to_group:
            continue
        base_slug = domain.split(".")[0]
        slug = base_slug
        counter = 1
        while slug in used_slugs:
            counter += 1
            slug = f"{base_slug}{counter}"
        used_slugs.add(slug)
        group_id = uuidlib.uuid4()
        domain_to_group[domain] = group_id
        conn.execute(
            sa.text(
                "INSERT INTO groups (id, slug, name, email_domain)"
                " VALUES (:id, :slug, :name, :domain)"
            ),
            {"id": group_id, "slug": slug, "name": base_slug.capitalize(), "domain": domain},
        )

    user_group: dict[uuidlib.UUID, uuidlib.UUID] = {}
    user_branch: dict[uuidlib.UUID, str] = {}
    for user in users:
        domain = user.email.split("@")[1].lower()
        group_id = domain_to_group[domain]
        user_group[user.id] = group_id
        user_branch[user.id] = user.branch
        conn.execute(
            sa.text("UPDATE users SET group_id = :g WHERE id = :i"),
            {"g": group_id, "i": user.id},
        )

    # 3b. One cassa per (group, unit), created on demand.
    cassa_map: dict[tuple[uuidlib.UUID, str], uuidlib.UUID] = {}

    def ensure_cassa(group_id: uuidlib.UUID, unit: str) -> uuidlib.UUID:
        key = (group_id, unit)
        if key not in cassa_map:
            cassa_id = uuidlib.uuid4()
            cassa_map[key] = cassa_id
            conn.execute(
                sa.text("INSERT INTO casse (id, group_id, unit) VALUES (:id, :g, :u)"),
                {"id": cassa_id, "g": group_id, "u": unit},
            )
        return cassa_map[key]

    for user in users:
        ensure_cassa(user_group[user.id], user.branch)

    # 3c. Scope movements by (creator group, movement unit).
    movements = conn.execute(sa.text("SELECT id, unit, created_by FROM movements")).all()
    for movement in movements:
        group_id = user_group.get(movement.created_by)
        if group_id is None:
            continue
        cassa_id = ensure_cassa(group_id, movement.unit)
        conn.execute(
            sa.text("UPDATE movements SET cassa_id = :c WHERE id = :i"),
            {"c": cassa_id, "i": movement.id},
        )

    # 3d. Scope transfers by creator group + branch (best effort, treasury-level).
    transfers = conn.execute(sa.text("SELECT id, created_by FROM treasury_transfers")).all()
    for transfer in transfers:
        group_id = user_group.get(transfer.created_by)
        if group_id is None:
            continue
        cassa_id = ensure_cassa(group_id, user_branch[transfer.created_by])
        conn.execute(
            sa.text("UPDATE treasury_transfers SET cassa_id = :c WHERE id = :i"),
            {"c": cassa_id, "i": transfer.id},
        )

    # 3e. One membership per user on their (group, branch) cassa.
    for user in users:
        cassa_id = ensure_cassa(user_group[user.id], user.branch)
        conn.execute(
            sa.text(
                "INSERT INTO memberships (id, user_id, cassa_id, role)"
                " VALUES (:id, :u, :c, :r)"
            ),
            {"id": uuidlib.uuid4(), "u": user.id, "c": cassa_id, "r": user.role},
        )

    # 3f. Existing (global) camp settings -> primary cassa (first admin's cassa).
    settings_rows = conn.execute(sa.text("SELECT id FROM camp_settings")).all()
    if settings_rows and users:
        primary_user = next((u for u in users if u.role == "ADMIN"), users[0])
        primary_cassa = ensure_cassa(user_group[primary_user.id], primary_user.branch)
        for row in settings_rows:
            conn.execute(
                sa.text("UPDATE camp_settings SET cassa_id = :c WHERE id = :i"),
                {"c": primary_cassa, "i": row.id},
            )

    # 4. Enforce NOT NULL now that everything is backfilled -------------------
    op.alter_column("users", "group_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("movements", "cassa_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("treasury_transfers", "cassa_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("camp_settings", "cassa_id", existing_type=sa.Uuid(), nullable=False)

    # 5. Role and branch now live on memberships ------------------------------
    op.drop_column("users", "branch")
    op.drop_column("users", "role")


def downgrade() -> None:
    conn = op.get_bind()

    op.add_column("users", sa.Column("role", userrole, nullable=True))
    op.add_column("users", sa.Column("branch", sa.String(50), nullable=True))

    rows = conn.execute(
        sa.text(
            "SELECT DISTINCT ON (m.user_id) m.user_id AS user_id, m.role AS role, c.unit AS unit"
            " FROM memberships m JOIN casse c ON c.id = m.cassa_id"
            " ORDER BY m.user_id, m.created_at"
        )
    ).all()
    for row in rows:
        conn.execute(
            sa.text("UPDATE users SET role = :r, branch = :b WHERE id = :i"),
            {"r": row.role, "b": row.unit, "i": row.user_id},
        )
    conn.execute(sa.text("UPDATE users SET role = 'USER' WHERE role IS NULL"))
    conn.execute(sa.text("UPDATE users SET branch = 'E/G' WHERE branch IS NULL"))

    op.alter_column("users", "role", existing_type=userrole, nullable=False)
    op.alter_column("users", "branch", existing_type=sa.String(50), nullable=False)

    op.drop_column("camp_settings", "cassa_id")
    op.drop_column("treasury_transfers", "cassa_id")
    op.drop_column("movements", "cassa_id")
    op.drop_column("users", "group_id")

    op.drop_index("ix_memberships_cassa_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_casse_group_id", table_name="casse")
    op.drop_table("casse")
    op.drop_index("ix_groups_email_domain", table_name="groups")
    op.drop_index("ix_groups_slug", table_name="groups")
    op.drop_table("groups")
