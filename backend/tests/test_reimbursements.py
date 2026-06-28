from datetime import date
from decimal import Decimal

from app.models import (
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    UserRole,
)
from app.routers.reimbursements import list_reimbursements, update_reimbursement
from app.schemas import ReimbursementUpdate


def reimbursable(cassa, user, supplier, amount):
    return Movement(
        cassa_id=cassa.id,
        operation_date=date.today(),
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier=supplier,
        unit=cassa.unit,
        category="vitto",
        amount=Decimal(amount),
        notes="Spesa",
        created_by=user.id,
        reimbursement=MovementReimbursement(),
    )


def test_users_see_only_their_reimbursements_and_operators_can_complete_them(
    db, make_group, make_cassa, make_user, membership_of
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    admin = make_user(group, "admin@roma108.it", memberships=[(cassa, UserRole.ADMIN)])
    cashier = make_user(group, "cashier@roma108.it", memberships=[(cassa, UserRole.CASHIER)])
    first_user = make_user(group, "first@roma108.it", memberships=[(cassa, UserRole.USER)])
    second_user = make_user(group, "second@roma108.it", memberships=[(cassa, UserRole.USER)])

    first_movement = reimbursable(cassa, first_user, "Prima spesa", "12.50")
    second_movement = reimbursable(cassa, second_user, "Seconda spesa", "8.00")
    db.add_all([first_movement, second_movement])
    db.flush()

    user_summary = list_reimbursements(db, membership_of(first_user, cassa))
    admin_summary = list_reimbursements(db, membership_of(admin, cassa))
    cashier_summary = list_reimbursements(db, membership_of(cashier, cassa))
    completed = update_reimbursement(
        first_movement.id,
        ReimbursementUpdate(reimbursed=True),
        db,
        membership_of(admin, cassa),
    )

    assert user_summary.pending_amount == Decimal("12.50")
    assert [movement.creator_email for movement in user_summary.movements] == ["first@roma108.it"]
    assert admin_summary.pending_amount == Decimal("20.50")
    assert cashier_summary.pending_amount == Decimal("20.50")
    assert completed.pending_amount == Decimal("8.00")
    assert completed.reimbursed_amount == Decimal("12.50")
