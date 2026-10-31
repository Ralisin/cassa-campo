import uuid
from datetime import timedelta
from decimal import Decimal

from app.models import (
    BalanceType,
    CampCategoryBudget,
    CampSettings,
    CassaKind,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    Branch,
    UserRole,
)
from app.schemas import MovementInput
from app.services import apply_movement_input, camp_today, get_dashboard


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


def test_group_expenses_reduce_cash_but_not_unit_budget(
    db, make_group, make_cassa, make_user
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    user = make_user(group, "utente@roma108.it", memberships=[(cassa, UserRole.USER)])
    settings_id = uuid.uuid4()
    db.add_all([
        CampSettings(
            id=settings_id, cassa_id=cassa.id, camp_year=2026, camp_name="Campo",
            participants=10, quota_per_person=Decimal("100"), max_budget=Decimal("1000"),
            cash_initial=Decimal("700"), bank_initial=Decimal("300"),
        ),
        CampCategoryBudget(settings_id=settings_id, category="alloggio", amount=Decimal("400")),
    ])
    for supplier, amount, unit, balance_type in [
        ("Spesa E/G", "50", "E/G", BalanceType.CAMP),
        ("Spesa Gruppo", "600", "Gruppo", BalanceType.CAMP),
        ("Bilancio ordinario", "20", "E/G", BalanceType.ORDINARY),
    ]:
        db.add(Movement(
            cassa_id=cassa.id, operation_date=camp_today(), type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH, supplier=supplier, unit=unit,
            balance_type=balance_type, category="alloggio", amount=Decimal(amount),
            created_by=user.id,
        ))
    db.flush()

    dashboard = get_dashboard(db, cassa.id)

    assert dashboard.cash_balance == Decimal("30.00")
    assert dashboard.spent == Decimal("70.00")
    assert dashboard.remaining_budget == Decimal("930.00")
    alloggio = next(row for row in dashboard.category_summaries if row.category == "alloggio")
    assert alloggio.spent == Decimal("70.00")
    assert alloggio.budget == Decimal("400.00")
    assert not any(item.kind == "high_expense" for item in dashboard.anomalies)


def test_annual_eg_dashboard_excludes_group_expense_from_spending(
    db, make_group, make_cassa, make_user
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    cassa.kind = CassaKind.ANNO
    user = make_user(group, "utente@roma108.it", memberships=[(cassa, UserRole.USER)])
    db.add_all([
        CampSettings(
            cassa_id=cassa.id, camp_year=2026, camp_name="Reparto",
            participants=1, quota_per_person=Decimal("3280"), max_budget=Decimal("3280"),
            cash_initial=Decimal("0"), bank_initial=Decimal("3280"),
        ),
        Movement(
            cassa_id=cassa.id, operation_date=camp_today(), type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH, supplier="Orso Scout", unit="Gruppo",
            category="alloggio", amount=Decimal("600"), created_by=user.id,
        ),
    ])
    db.flush()

    dashboard = get_dashboard(db, cassa.id)

    assert dashboard.cash_balance == Decimal("-600")
    assert dashboard.bank_balance == Decimal("3280")
    assert dashboard.spent == Decimal("0")
    assert dashboard.remaining_budget == Decimal("3280")
    assert all(row.spent == 0 for row in dashboard.category_summaries)
    assert dashboard.today_movements == []
    assert not dashboard.anomalies


def test_camp_movement_can_be_attributed_to_group_without_changing_paying_cassa(
    db, make_group, make_cassa, make_user
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    user = make_user(group, "utente@roma108.it", memberships=[(cassa, UserRole.USER)])
    movement = Movement(created_by=user.id)
    data = MovementInput(
        operation_date=camp_today(), type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH, supplier="Spesa Gruppo", unit=Branch.GRUPPO,
        balance_type=BalanceType.CAMP, category="alloggio", amount=Decimal("600"),
        notes="Pagata dai contanti E/G",
    )

    apply_movement_input(movement, data, cassa, UserRole.USER)

    assert movement.cassa_id == cassa.id
    assert movement.unit == "Gruppo"
