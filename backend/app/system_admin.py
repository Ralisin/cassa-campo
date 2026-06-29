from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Group, User

SYSTEM_GROUP_SLUG = "sistema"
SYSTEM_GROUP_NAME = "Amministrazione sistema"


def ensure_system_admin(db: Session) -> None:
    email = settings.system_admin_email.strip().lower()
    domain = email.split("@")[-1]
    group = db.scalar(select(Group).where(Group.email_domain == domain))
    if group is None:
        slug = SYSTEM_GROUP_SLUG
        counter = 1
        while db.scalar(select(Group).where(Group.slug == slug)):
            counter += 1
            slug = f"{SYSTEM_GROUP_SLUG}-{counter}"
        group = Group(slug=slug, name=SYSTEM_GROUP_NAME, email_domain=domain)
        db.add(group)
        db.flush()

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        db.add(
            User(
                email=email,
                name=settings.system_admin_name.strip() or "System admin",
                password_hash=hash_password(settings.system_admin_password),
                group_id=group.id,
                is_system_admin=True,
            )
        )
    elif not user.is_system_admin:
        user.is_system_admin = True

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
