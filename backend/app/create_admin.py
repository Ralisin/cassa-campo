import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Branch, Cassa, CassaKind, CassaStatus, Group, Membership, User, UserRole


def main() -> None:
    if len(sys.argv) != 5:
        branches = ", ".join(branch.value for branch in Branch)
        raise SystemExit(
            f"Usage: python -m app.create_admin EMAIL NAME PASSWORD BRANCH\nBranches: {branches}"
        )
    email, name, password, branch_value = sys.argv[1:]
    email = email.strip().lower()
    try:
        branch = Branch(branch_value)
    except ValueError as exc:
        raise SystemExit(f"Invalid branch: {branch_value}") from exc
    if "@" not in email:
        raise SystemExit("Invalid email")
    domain = email.split("@")[1]

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("User already exists")

        group = db.scalar(select(Group).where(Group.email_domain == domain))
        if group is None:
            slug = domain.split(".")[0]
            group = Group(slug=slug, name=slug.capitalize(), email_domain=domain)
            db.add(group)
            db.flush()

        cassa = db.scalar(
            select(Cassa).where(
                Cassa.group_id == group.id,
                Cassa.unit == branch.value,
                Cassa.kind == CassaKind.CAMPO,
                Cassa.status == CassaStatus.OPEN,
            )
        )
        if cassa is None:
            cassa = Cassa(group_id=group.id, unit=branch.value, kind=CassaKind.CAMPO)
            db.add(cassa)
            db.flush()

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            group_id=group.id,
        )
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, cassa_id=cassa.id, role=UserRole.ADMIN))
        db.commit()
    print(f"Admin created: {email} (group {group.slug}, cassa {branch.value})")


if __name__ == "__main__":
    main()
