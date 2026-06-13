import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Movement, MovementType, PaymentMethod, User, UserRole
from app.services import camp_today, get_dashboard


def test_dashboard_contains_only_movements_from_today() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = User(
            id=uuid.uuid4(),
            email="utente@example.it",
            name="Utente",
            password_hash="unused",
            role=UserRole.USER,
            branch="E/G",
        )
        db.add(user)
        db.add_all(
            [
                Movement(
                    operation_date=camp_today(),
                    type=MovementType.EXPENSE,
                    payment_method=PaymentMethod.CASH,
                    supplier="Movimento di oggi",
                    unit="Gruppo",
                    amount=Decimal("10.00"),
                    created_by=user.id,
                ),
                Movement(
                    operation_date=camp_today() - timedelta(days=1),
                    type=MovementType.EXPENSE,
                    payment_method=PaymentMethod.CASH,
                    supplier="Movimento di ieri",
                    unit="Gruppo",
                    amount=Decimal("5.00"),
                    created_by=user.id,
                ),
            ]
        )
        db.commit()

        dashboard = get_dashboard(db)

    assert [movement.supplier for movement in dashboard.today_movements] == ["Movimento di oggi"]
