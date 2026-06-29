from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import CurrentUser, DbSession
from app.models import User
from app.schemas import LoginRequest, PasswordChange, Token, UserRead
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
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
