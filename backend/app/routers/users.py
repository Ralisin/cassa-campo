import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.dependencies import AdminUser, DbSession
from app.models import User, UserRole
from app.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def get_user_or_404(db: DbSession, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def commit_user(db: DbSession, user: User) -> User:
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email già utilizzata",
        ) from exc
    return user


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name, User.email)).all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DbSession, _: AdminUser) -> User:
    user = User(
        email=str(data.email).lower(),
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        role=data.role,
        branch=data.branch.value,
    )
    return commit_user(db, user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, data: UserUpdate, db: DbSession, _: AdminUser) -> User:
    user = get_user_or_404(db, user_id)
    if user.role == UserRole.ADMIN and data.role != UserRole.ADMIN:
        admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN))
        if admin_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'ultimo admin non può essere trasformato in utente",
            )

    user.email = str(data.email).lower()
    user.name = data.name.strip()
    user.role = data.role
    user.branch = data.branch.value
    if data.password:
        user.password_hash = hash_password(data.password)
    return commit_user(db, user)
