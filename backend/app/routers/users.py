import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.audit_service import write_audit
from app.core.security import hash_password
from app.dependencies import AdminMembership, CurrentUser, DbSession
from app.models import Cassa, CassaKind, CassaStatus, Group, Membership, User, UserRole
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
        .where(User.id == user_id, User.group_id == group_id, User.deleted_at.is_(None))
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def ensure_cassa(
    db: DbSession, group_id: uuid.UUID, unit: str, kind: CassaKind = CassaKind.CAMPO
) -> Cassa:
    cassa = db.scalar(
        select(Cassa).where(
            Cassa.group_id == group_id,
            Cassa.unit == unit,
            Cassa.kind == kind,
            Cassa.status == CassaStatus.OPEN,
        )
    )
    if cassa is None:
        cassa = Cassa(group_id=group_id, unit=unit, kind=kind)
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
    desired = {}
    units = set()
    for item in memberships:
        if item.cassa_id is not None:
            cassa = db.scalar(
                select(Cassa).where(Cassa.id == item.cassa_id, Cassa.group_id == group.id)
            )
            if cassa is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cassa non valida")
        elif item.unit is not None:
            cassa = ensure_cassa(db, group.id, item.unit.value, item.kind)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cassa obbligatoria")
        if cassa.unit in units:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unità ripetuta")
        units.add(cassa.unit)
        for unit_cassa in db.scalars(select(Cassa).where(Cassa.group_id == group.id, Cassa.unit == cassa.unit)):
            desired[unit_cassa.id] = (unit_cassa, item.role)

    existing = {membership.cassa_id: membership for membership in user.memberships}
    for cassa_id, membership in existing.items():
        if cassa_id not in desired:
            guard_last_admin(db, membership)
            user.memberships.remove(membership)

    for cassa_id, (cassa, role) in desired.items():
        membership = existing.get(cassa_id)
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
def list_users(db: DbSession, _admin: CurrentUser, admin_membership: AdminMembership) -> list[UserRead]:
    group_id = admin_membership.cassa.group_id
    users = db.scalars(
        select(User)
        .options(selectinload(User.memberships).joinedload(Membership.cassa).joinedload(Cassa.group))
        .where(User.group_id == group_id, User.is_system_admin.is_(False), User.deleted_at.is_(None))
        .order_by(User.name, User.email)
    ).all()
    return [user_to_read(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate, db: DbSession, _admin: CurrentUser, admin_membership: AdminMembership
) -> UserRead:
    group = get_group_or_404(db, admin_membership.cassa.group_id)
    email = validate_email_domain(str(data.email), group)
    user = User(
        email=email,
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        group_id=group.id,
    )
    db.add(user)
    sync_memberships(db, user, group, data.memberships)
    db.flush()
    write_audit(
        db,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        cassa_id=admin_membership.cassa_id,
        user_id=admin_membership.user_id,
        summary=f"Creato utente {user.email}",
    )
    return user_to_read(commit_user(db, user))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    db: DbSession,
    admin_membership: AdminMembership,
) -> Response:
    user = get_user_in_group_or_404(db, user_id, admin_membership.cassa.group_id)
    if user.is_system_admin or user.id == admin_membership.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi eliminare questo utente")
    for membership in user.memberships:
        guard_last_admin(db, membership)
    user.memberships.clear()
    user.deleted_at = datetime.now(UTC)
    user.email = f"deleted-{user.id}@deleted.invalid"
    # Keep the creator's name attached to historical movements and reimbursements.
    write_audit(
        db,
        action="user_deleted",
        entity_type="user",
        entity_id=user.id,
        cassa_id=admin_membership.cassa_id,
        user_id=admin_membership.user_id,
        summary="Utente eliminato",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: DbSession,
    _admin: CurrentUser,
    admin_membership: AdminMembership,
) -> UserRead:
    group = get_group_or_404(db, admin_membership.cassa.group_id)
    user = get_user_in_group_or_404(db, user_id, group.id)
    if user.is_system_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.email = validate_email_domain(str(data.email), group)
    user.name = data.name.strip()
    if data.password:
        user.password_hash = hash_password(data.password)
    sync_memberships(db, user, group, data.memberships)
    write_audit(
        db,
        action="user_updated",
        entity_type="user",
        entity_id=user.id,
        cassa_id=admin_membership.cassa_id,
        user_id=admin_membership.user_id,
        summary=f"Aggiornato utente {user.email}",
        details={"password_changed": bool(data.password)},
    )
    return user_to_read(commit_user(db, user))
