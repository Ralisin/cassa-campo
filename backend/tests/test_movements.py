import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fastapi import HTTPException
import pytest

from app.core.database import Base
from app.models import (
    Movement,
    MovementReimbursement,
    MovementType,
    Notification,
    PaymentMethod,
    User,
    UserRole,
)
from app.routers.movements import delete_movement, list_movements


def make_user(name: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{name.lower()}@example.it",
        name=name,
        password_hash="unused",
        role=UserRole.USER,
        branch="E/G",
    )


def make_movement(user: User, supplier: str, day: date, created_at: datetime) -> Movement:
    return Movement(
        id=uuid.uuid4(),
        operation_date=day,
        created_at=created_at,
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier=supplier,
        unit="E/G",
        amount=Decimal("10.00"),
        notes="Spesa campo",
        created_by=user.id,
    )


def test_list_movements_paginates_and_filters() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now()

    with Session(engine) as db:
        alice = make_user("Alice")
        bob = make_user("Bob")
        db.add_all([alice, bob])
        db.flush()
        movements = [
            make_movement(alice, "Più recente", date.today(), now),
            make_movement(bob, "Secondo", date.today(), now - timedelta(minutes=1)),
            make_movement(alice, "Più vecchio", date.today() - timedelta(days=1), now),
        ]
        movements[1].reimbursement = MovementReimbursement()
        db.add_all(movements)
        db.commit()

        first_page = list_movements(db, alice, limit=2)
        second_page = list_movements(db, alice, cursor=first_page.next_cursor, limit=2)
        filtered = list_movements(db, alice, query="bob", reimbursement="da_rimborsare")

    assert [item.supplier for item in first_page.items] == ["Più recente", "Secondo"]
    assert [item.supplier for item in second_page.items] == ["Più vecchio"]
    assert first_page.total == 3
    assert first_page.next_cursor
    assert second_page.next_cursor is None
    assert [item.supplier for item in filtered.items] == ["Secondo"]
    assert {creator.name for creator in filtered.creators} == {"Alice", "Bob"}


def test_list_movements_rejects_invalid_cursor() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db, pytest.raises(HTTPException) as error:
        list_movements(db, make_user("Alice"), cursor="not-a-cursor")

    assert error.value.status_code == 422


def test_user_can_delete_own_movement_and_related_notifications() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        owner = make_user("Alice")
        admin = make_user("Admin")
        admin.role = UserRole.ADMIN
        movement = make_movement(owner, "Supermercato", date.today(), datetime.now())
        notification = Notification(
            user=admin,
            movement=movement,
            kind="movement_created",
            title="Nuovo movimento",
            message="Alice ha aggiunto Supermercato.",
        )
        db.add_all([owner, admin, movement, notification])
        db.commit()
        movement_id = movement.id
        notification_id = notification.id

        response = delete_movement(movement_id, db, owner)

        assert response.status_code == 204
        assert db.get(Movement, movement_id) is None
        assert db.get(Notification, notification_id) is None


def test_user_cannot_delete_another_users_movement() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        owner = make_user("Alice")
        other_user = make_user("Bob")
        movement = make_movement(owner, "Supermercato", date.today(), datetime.now())
        db.add_all([owner, other_user, movement])
        db.commit()
        movement_id = movement.id

        with pytest.raises(HTTPException) as error:
            delete_movement(movement_id, db, other_user)

        assert error.value.status_code == 403
        assert db.get(Movement, movement_id) is not None
