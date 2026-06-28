import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.dependencies import AdminMembership, CurrentUser, DbSession
from app.models import Cassa, Group, Membership, User, UserRole
from app.schemas import MembershipInput, UserCreate, UserRead, UserUpdate
from app.services import user_to_read

router = APIRouter(prefix="/users", tags=["users"])


def get_group_or_404(db: DbSession, group_id: uuid.UUID) -> Group:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


def get_user_in_group_or_404(db: DbSession, user_id: uuid.UUID, group_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User)
        .options(selectinload(User.memberships).joinedload(Membership.cassa).joinedload(Cassa.group))
        .where(User.id == user_id, User.group_id == group_id)
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def ensure_cassa(db: DbSession, group_id: uuid.UUID, unit: str) -> Cassa:
    cassa = db.scalar(select(Cassa).where(Cassa.group_id == group_id, Cassa.unit == unit))
    if cassa is None:
        cassa = Cassa(group_id=group_id, unit=unit)
        db.add(cassa)
        db.flush()
    return cassa


def validate_email_domain(email: str, group: Group) -> str:
    email = email.strip().lower()
    if email.split("@")[-1] != group.email_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'email deve appartenere al dominio @{group.email_domain}",
        )
    return email


def sync_memberships(
    db: DbSession, user: User, group: Group, memberships: list[MembershipInput]
) -> None:
    desired = {item.unit.value: item.role for item in memberships}
    existing = {membership.cassa.unit: membership for membership in user.memberships}

    for unit, membership in list(existing.items()):
        if unit not in desired:
            guard_last_admin(db, membership)
            user.memberships.remove(membership)

    for unit, role in desired.items():
        cassa = ensure_cassa(db, group.id, unit)
        membership = existing.get(unit)
        if membership is None:
            user.memberships.append(Membership(cassa_id=cassa.id, role=role))
        elif membership.role != role:
            if membership.role == UserRole.ADMIN and role != UserRole.ADMIN:
                guard_last_admin(db, membership)
            membership.role = role


def guard_last_admin(db: DbSession, membership: Membership) -> None:
    if membership.role != UserRole.ADMIN:
        return
    admin_count = db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.cassa_id == membership.cassa_id, Membership.role == UserRole.ADMIN)
    )
    if admin_count == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non puoi rimuovere l'ultimo admin di una cassa",
        )


def commit_user(db: DbSession, user: User) -> User:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email già utilizzata",
        ) from exc
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession, admin: CurrentUser, _: AdminMembership) -> list[UserRead]:
    users = db.scalars(
        select(User)
        .options(selectinload(User.memberships).joinedload(Membership.cassa).joinedload(Cassa.group))
        .where(User.group_id == admin.group_id)
        .order_by(User.name, User.email)
    ).all()
    return [user_to_read(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DbSession, admin: CurrentUser, _: AdminMembership) -> UserRead:
    group = get_group_or_404(db, admin.group_id)
    email = validate_email_domain(str(data.email), group)
    user = User(
        email=email,
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        group_id=group.id,
    )
    db.add(user)
    sync_memberships(db, user, group, data.memberships)
    return user_to_read(commit_user(db, user))


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID, data: UserUpdate, db: DbSession, admin: CurrentUser, _: AdminMembership
) -> UserRead:
    group = get_group_or_404(db, admin.group_id)
    user = get_user_in_group_or_404(db, user_id, group.id)
    user.email = validate_email_domain(str(data.email), group)
    user.name = data.name.strip()
    if data.password:
        user.password_hash = hash_password(data.password)
    sync_memberships(db, user, group, data.memberships)
    return user_to_read(commit_user(db, user))
