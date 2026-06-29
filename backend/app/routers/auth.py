from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.audit_service import write_audit
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import CurrentUser, DbSession
from app.models import PasswordResetToken, User
from app.password_reset import create_password_reset_token, hash_reset_token, send_password_reset_email
from app.schemas import (
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserRead,
)
from app.services import user_to_read

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: DbSession) -> Token:
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return user_to_read(user)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, db: DbSession, user: CurrentUser) -> Response:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password attuale non corretta",
        )
    user.password_hash = hash_password(data.new_password)
    write_audit(
        db,
        action="password_changed",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        cassa_id=None,
        summary=f"{user.name} ha cambiato password",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
def request_password_reset(data: PasswordResetRequest, db: DbSession) -> Response:
    user = db.scalar(select(User).where(User.email == data.email))
    if user:
        token = create_password_reset_token(db, user)
        write_audit(
            db,
            action="password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            summary=f"Richiesto reset password per {user.email}",
        )
        db.commit()
        send_password_reset_email(user.email, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(data: PasswordResetConfirm, db: DbSession) -> Response:
    now = datetime.now(UTC)
    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(data.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link di reset non valido o scaduto",
        )
    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utente non trovato")
    user.password_hash = hash_password(data.new_password)
    reset.used_at = now
    write_audit(
        db,
        action="password_reset_completed",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        summary=f"Password reimpostata per {user.email}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
