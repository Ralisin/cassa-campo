from datetime import date
from decimal import Decimal

from app.models import MovementType, PaymentMethod, UserRole
from app.routers.movements import create_movement
from app.routers.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.routers.reimbursements import update_reimbursement
from app.schemas import MovementInput, ReimbursementUpdate


def test_reimbursement_notifications_reach_admin_cashier_and_requesting_user(
    db, make_group, make_cassa, make_user, membership_of
) -> None:
    group = make_group()
    eg = make_cassa(group, "E/G")
    rs = make_cassa(group, "R/S")
    admin = make_user(group, "admin@roma108.it", memberships=[(eg, UserRole.ADMIN)])
    cashier = make_user(group, "cashier@roma108.it", memberships=[(eg, UserRole.CASHIER)])
    other_cashier = make_user(group, "altro@roma108.it", memberships=[(rs, UserRole.CASHIER)])
    user = make_user(group, "user@roma108.it", memberships=[(eg, UserRole.USER)])

    admin_eg = membership_of(admin, eg)
    cashier_eg = membership_of(cashier, eg)
    other_rs = membership_of(other_cashier, rs)
    user_eg = membership_of(user, eg)

    movement = create_movement(
        MovementInput(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Supermercato",
            category="vitto",
            amount=Decimal("24.50"),
            notes="Spesa cambusa",
            needs_reimbursement=True,
        ),
        db,
        user_eg,
    )

    admin_notifications = list_notifications(db, admin_eg)
    assert admin_notifications.unread_count == 1
    assert admin_notifications.items[0].kind == "reimbursement_requested"
    assert list_notifications(db, cashier_eg).unread_count == 1
    # a cashier of a different cassa is not notified
    assert list_notifications(db, other_rs).unread_count == 0

    mark_notification_read(admin_notifications.items[0].id, db, admin)
    assert list_notifications(db, admin_eg).unread_count == 0

    create_movement(
        MovementInput(
            operation_date=date.today(),
            type=MovementType.INCOME,
            payment_method=PaymentMethod.CASH,
            supplier="Quota partecipante",
            amount=Decimal("10.00"),
            notes="Quota",
        ),
        db,
        user_eg,
    )
    admin_notifications = list_notifications(db, admin_eg)
    assert admin_notifications.unread_count == 1
    unread = next(item for item in admin_notifications.items if item.read_at is None)
    assert unread.kind == "movement_created"
    assert list_notifications(db, cashier_eg).unread_count == 1
    mark_all_notifications_read(db, admin_eg)

    update_reimbursement(movement.id, ReimbursementUpdate(reimbursed=True), db, admin_eg)
    user_notifications = list_notifications(db, user_eg)
    assert user_notifications.unread_count == 1
    assert user_notifications.items[0].kind == "reimbursement_completed"
    assert "24,50" in user_notifications.items[0].message

    mark_all_notifications_read(db, user_eg)
    assert list_notifications(db, user_eg).unread_count == 0
