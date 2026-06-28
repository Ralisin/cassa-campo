import uuid
from datetime import timedelta
from decimal import Decimal

from app.models import (
    CampCategoryBudget,
    CampSettings,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    UserRole,
)
from app.services import camp_today, get_dashboard


def test_dashboard_contains_only_movements_from_today(db, make_group, make_cassa, make_user) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    user = make_user(group, "utente@roma108.it", memberships=[(cassa, UserRole.USER)])

    settings_id = uuid.uuid4()
    db.add_all(
        [
            CampSettings(
                id=settings_id,
                cassa_id=cassa.id,
                camp_year=2026,
                camp_name="Campo",
                participants=10,
                quota_per_person=Decimal("100"),
                max_budget=Decimal("1000"),
                cash_initial=Decimal("100"),
                bank_initial=Decimal("900"),
            ),
            CampCategoryBudget(settings_id=settings_id, category="vitto", amount=Decimal("300")),
            Movement(
                cassa_id=cassa.id,
                operation_date=camp_today(),
                type=MovementType.EXPENSE,
                payment_method=PaymentMethod.CASH,
                supplier="Movimento di oggi",
                unit=cassa.unit,
                category="vitto",
                amount=Decimal("10.00"),
                created_by=user.id,
                reimbursement=MovementReimbursement(),
            ),
            Movement(
                cassa_id=cassa.id,
                operation_date=camp_today() - timedelta(days=1),
                type=MovementType.EXPENSE,
                payment_method=PaymentMethod.CASH,
                supplier="Movimento di ieri",
                unit=cassa.unit,
                category="alloggio",
                amount=Decimal("5.00"),
                created_by=user.id,
            ),
        ]
    )
    db.flush()

    dashboard = get_dashboard(db, cassa.id)

    assert [movement.supplier for movement in dashboard.today_movements] == ["Movimento di oggi"]
    summaries = {item.category: (item.spent, item.budget) for item in dashboard.category_summaries}
    assert summaries["vitto"] == (Decimal("10.00"), Decimal("300.00"))
    assert summaries["alloggio"] == (Decimal("5.00"), Decimal("0.00"))
    assert dashboard.pending_reimbursements == Decimal("10.00")
    assert dashboard.spent == Decimal("15.00")
