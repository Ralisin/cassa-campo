import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password, verify_password
from app.models import Branch, User, UserRole
from app.routers.users import create_user, update_user
from app.schemas import UserCreate, UserUpdate


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def admin() -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@example.it",
        name="Admin",
        password_hash=hash_password("password"),
        role=UserRole.ADMIN,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )


def test_admin_can_create_and_update_user(db: Session) -> None:
    current_admin = admin()
    db.add(current_admin)
    db.commit()

    user = create_user(
        UserCreate(
            email="UTENTE@example.it",
            name="Utente",
            password="password",
            role=UserRole.USER,
            branch=Branch.ROVER_SCOLTE,
        ),
        db,
        current_admin,
    )
    original_hash = user.password_hash

    updated = update_user(
        user.id,
        UserUpdate(
            email="nuova@example.it",
            name="Nuovo Nome",
            password="nuova-password",
            role=UserRole.ADMIN,
            branch=Branch.COCA,
        ),
        db,
        current_admin,
    )

    assert user.email == "nuova@example.it"
    assert updated.name == "Nuovo Nome"
    assert updated.role == UserRole.ADMIN
    assert updated.branch == Branch.COCA.value
    assert updated.password_hash != original_hash
    assert verify_password("nuova-password", updated.password_hash)


def test_last_admin_cannot_be_demoted(db: Session) -> None:
    current_admin = admin()
    db.add(current_admin)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_user(
            current_admin.id,
            UserUpdate(
                email=current_admin.email,
                name=current_admin.name,
                role=UserRole.USER,
                branch=Branch.ESPLORATORI_GUIDE,
            ),
            db,
            current_admin,
        )

    assert exc_info.value.status_code == 400
