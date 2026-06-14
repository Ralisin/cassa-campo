import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    CampCategoryBudget,
    CampSettings,
    ExpenseCategory,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    User,
    UserRole,
)
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
                ExpenseCategory(slug="vitto", label="Vitto", position=1),
                ExpenseCategory(slug="alloggio", label="Alloggio", position=2),
                CampSettings(
                    id=(settings_id := uuid.uuid4()),
                    camp_year=2026,
                    camp_name="Campo",
                    participants=10,
                    quota_per_person=Decimal("100"),
                    max_budget=Decimal("1000"),
                    cash_initial=Decimal("100"),
                    bank_initial=Decimal("900"),
                ),
                CampCategoryBudget(
                    settings_id=settings_id,
                    category="vitto",
                    amount=Decimal("300"),
                ),
            ]
        )
        db.add_all(
            [
                Movement(
                    operation_date=camp_today(),
                    type=MovementType.EXPENSE,
                    payment_method=PaymentMethod.CASH,
                    supplier="Movimento di oggi",
                    unit="Gruppo",
                    category="vitto",
                    amount=Decimal("10.00"),
                    created_by=user.id,
                    reimbursement=MovementReimbursement(),
                ),
                Movement(
                    operation_date=camp_today() - timedelta(days=1),
                    type=MovementType.EXPENSE,
                    payment_method=PaymentMethod.CASH,
                    supplier="Movimento di ieri",
                    unit="Gruppo",
                    category="alloggio",
                    amount=Decimal("5.00"),
                    created_by=user.id,
                ),
            ]
        )
        db.commit()

        dashboard = get_dashboard(db)

    assert [movement.supplier for movement in dashboard.today_movements] == ["Movimento di oggi"]
    assert [(item.category, item.spent, item.budget) for item in dashboard.category_summaries] == [
        ("vitto", Decimal("10.00"), Decimal("300.00")),
        ("alloggio", Decimal("5.00"), Decimal("0.00")),
    ]
    assert dashboard.pending_reimbursements == Decimal("10.00")
