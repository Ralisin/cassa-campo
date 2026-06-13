import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Branch, User, UserRole


def main() -> None:
    if len(sys.argv) != 5:
        branches = ", ".join(branch.value for branch in Branch)
        raise SystemExit(
            f"Usage: python -m app.create_admin EMAIL NAME PASSWORD BRANCH\nBranches: {branches}"
        )
    email, name, password, branch_value = sys.argv[1:]
    try:
        branch = Branch(branch_value)
    except ValueError as exc:
        raise SystemExit(f"Invalid branch: {branch_value}") from exc
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("User already exists")
        db.add(
            User(
                email=email,
                name=name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                branch=branch.value,
            )
        )
        db.commit()
    print(f"Admin created: {email}")


if __name__ == "__main__":
    main()
