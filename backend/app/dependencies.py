import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Cassa, Membership, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        user_id = uuid.UUID(decode_access_token(token))
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_membership(
    db: DbSession,
    user: CurrentUser,
    x_cassa_id: Annotated[uuid.UUID | None, Header(alias="X-Cassa-Id")] = None,
) -> Membership:
    if x_cassa_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Cassa-Id header",
        )
    membership = db.scalar(
        select(Membership)
        .options(joinedload(Membership.cassa).joinedload(Cassa.group))
        .where(Membership.user_id == user.id, Membership.cassa_id == x_cassa_id)
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this cassa",
        )
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]


def get_current_cassa(membership: CurrentMembership) -> Cassa:
    return membership.cassa


CurrentCassa = Annotated[Cassa, Depends(get_current_cassa)]


def require_admin(membership: CurrentMembership) -> Membership:
    if membership.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return membership


AdminMembership = Annotated[Membership, Depends(require_admin)]


def require_operator(membership: CurrentMembership) -> Membership:
    if membership.role not in (UserRole.ADMIN, UserRole.CASHIER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or cashier role required",
        )
    return membership


OperatorMembership = Annotated[Membership, Depends(require_operator)]


def can_edit_movement(membership: Membership, movement_created_by: uuid.UUID) -> bool:
    return (
        membership.role in (UserRole.ADMIN, UserRole.CASHIER)
        or movement_created_by == membership.user_id
    )
