import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Branch, MovementType, PaymentMethod, User, UserRole
from app.routers.movements import create_movement
from app.routers.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.routers.reimbursements import update_reimbursement
from app.schemas import MovementInput, ReimbursementUpdate


def make_user(email: str, role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        name=email.split("@")[0],
        password_hash="unused",
        role=role,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )


def test_reimbursement_notifications_reach_admin_and_requesting_user() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        admin = make_user("admin@example.it", UserRole.ADMIN)
        user = make_user("user@example.it", UserRole.USER)
        db.add_all([admin, user])
        db.commit()

        movement = create_movement(
            MovementInput(
                operation_date=date.today(),
                type=MovementType.EXPENSE,
                payment_method=PaymentMethod.CASH,
                supplier="Supermercato",
                unit=Branch.ESPLORATORI_GUIDE,
                amount=Decimal("24.50"),
                notes="Spesa cambusa",
                needs_reimbursement=True,
            ),
            db,
            user,
        )

        admin_notifications = list_notifications(db, admin)
        assert admin_notifications.unread_count == 1
        assert admin_notifications.items[0].kind == "reimbursement_requested"

        mark_notification_read(admin_notifications.items[0].id, db, admin)
        assert list_notifications(db, admin).unread_count == 0

        create_movement(
            MovementInput(
                operation_date=date.today(),
                type=MovementType.INCOME,
                payment_method=PaymentMethod.CASH,
                supplier="Quota partecipante",
                unit=Branch.ESPLORATORI_GUIDE,
                amount=Decimal("10.00"),
                notes="Quota",
            ),
            db,
            user,
        )
        admin_notifications = list_notifications(db, admin)
        assert admin_notifications.unread_count == 1
        unread_notification = next(item for item in admin_notifications.items if item.read_at is None)
        assert unread_notification.kind == "movement_created"
        mark_all_notifications_read(db, admin)

        update_reimbursement(
            movement.id,
            ReimbursementUpdate(reimbursed=True),
            db,
            admin,
        )
        user_notifications = list_notifications(db, user)
        assert user_notifications.unread_count == 1
        assert user_notifications.items[0].kind == "reimbursement_completed"
        assert "24,50" in user_notifications.items[0].message

        mark_all_notifications_read(db, user)
        assert list_notifications(db, user).unread_count == 0
