import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    Branch,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    User,
    UserRole,
)
from app.routers.reimbursements import list_reimbursements, update_reimbursement
from app.schemas import ReimbursementUpdate


def make_user(email: str, role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        name=email.split("@")[0],
        password_hash="unused",
        role=role,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )


def test_users_see_only_their_reimbursements_and_admin_can_complete_them() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        admin = make_user("admin@example.it", UserRole.ADMIN)
        first_user = make_user("first@example.it", UserRole.USER)
        second_user = make_user("second@example.it", UserRole.USER)
        db.add_all([admin, first_user, second_user])
        db.flush()
        first_movement = Movement(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Prima spesa",
            unit=Branch.ESPLORATORI_GUIDE.value,
            amount=Decimal("12.50"),
            notes="Spesa",
            created_by=first_user.id,
            reimbursement=MovementReimbursement(),
        )
        second_movement = Movement(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Seconda spesa",
            unit=Branch.ESPLORATORI_GUIDE.value,
            amount=Decimal("8.00"),
            notes="Spesa",
            created_by=second_user.id,
            reimbursement=MovementReimbursement(),
        )
        db.add_all([first_movement, second_movement])
        db.commit()

        user_summary = list_reimbursements(db, first_user)
        admin_summary = list_reimbursements(db, admin)
        completed = update_reimbursement(
            first_movement.id,
            ReimbursementUpdate(reimbursed=True),
            db,
            admin,
        )

    assert user_summary.pending_amount == Decimal("12.50")
    assert [movement.creator_email for movement in user_summary.movements] == ["first@example.it"]
    assert admin_summary.pending_amount == Decimal("20.50")
    assert completed.pending_amount == Decimal("8.00")
    assert completed.reimbursed_amount == Decimal("12.50")
