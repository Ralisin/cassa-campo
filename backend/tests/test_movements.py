import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.models import (
    Cassa,
    Movement,
    MovementReceipt,
    MovementReimbursement,
    MovementType,
    Notification,
    PaymentMethod,
    User,
    UserRole,
)
from app.routers.movements import delete_movement, list_deleted_movements, list_movements, restore_movement


def make_movement(
    cassa: Cassa, user: User, supplier: str, day: date, created_at: datetime
) -> Movement:
    return Movement(
        id=uuid.uuid4(),
        cassa_id=cassa.id,
        operation_date=day,
        created_at=created_at,
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier=supplier,
        unit=cassa.unit,
        category="vitto",
        amount=Decimal("10.00"),
        notes="Spesa campo",
        created_by=user.id,
    )


@pytest.fixture
def setup(db, make_group, make_cassa, make_user):
    group = make_group()
    cassa = make_cassa(group, "E/G")
    alice = make_user(group, "alice@roma108.it", memberships=[(cassa, UserRole.USER)])
    bob = make_user(group, "bob@roma108.it", memberships=[(cassa, UserRole.USER)])
    return db, group, cassa, alice, bob


def test_list_movements_paginates_and_filters(setup, membership_of) -> None:
    db, group, cassa, alice, bob = setup
    now = datetime(2026, 6, 20, 12, 0)
    movements = [
        make_movement(cassa, alice, "Più recente", date(2026, 6, 20), now),
        make_movement(cassa, bob, "Secondo", date(2026, 6, 20), now - timedelta(minutes=1)),
        make_movement(cassa, alice, "Più vecchio", date(2026, 6, 19), now),
    ]
    movements[1].reimbursement = MovementReimbursement()
    db.add_all(movements)
    db.flush()

    first_page = list_movements(db, cassa, limit=2)
    second_page = list_movements(db, cassa, cursor=first_page.next_cursor, limit=2)
    filtered = list_movements(db, cassa, query="bob", reimbursement="da_rimborsare")

    assert [item.supplier for item in first_page.items] == ["Più recente", "Secondo"]
    assert [item.supplier for item in second_page.items] == ["Più vecchio"]
    assert first_page.total == 3
    assert first_page.next_cursor
    assert second_page.next_cursor is None
    assert [item.supplier for item in filtered.items] == ["Secondo"]


def test_list_movements_rejects_invalid_cursor(setup) -> None:
    db, group, cassa, alice, bob = setup
    with pytest.raises(HTTPException) as error:
        list_movements(db, cassa, cursor="not-a-cursor")
    assert error.value.status_code == 422


def test_user_can_delete_own_movement_and_related_notifications(setup, membership_of) -> None:
    db, group, cassa, alice, bob = setup
    movement = make_movement(cassa, alice, "Supermercato", date.today(), datetime.now())
    notification = Notification(
        user=bob,
        movement=movement,
        kind="movement_created",
        title="Nuovo movimento",
        message="Alice ha aggiunto Supermercato.",
    )
    db.add_all([movement, notification])
    db.flush()
    movement_id, notification_id = movement.id, notification.id

    response = delete_movement(movement_id, db, membership_of(alice, cassa))

    assert response.status_code == 204
    assert db.get(Movement, movement_id).deleted_at is not None
    assert db.get(Notification, notification_id) is not None
    assert list_movements(db, cassa).items == []
    assert [item.id for item in list_deleted_movements(db, membership_of(alice, cassa))] == [movement_id]


def test_deleted_movement_can_be_restored_with_receipts(setup, membership_of) -> None:
    db, group, cassa, alice, bob = setup
    movement = make_movement(cassa, alice, "Supermercato", date.today(), datetime.now())
    receipt = MovementReceipt(
        id=uuid.uuid4(),
        movement=movement,
        uploaded_by=alice.id,
        filename="scontrino.pdf",
        content_type="application/pdf",
        size_bytes=128,
        storage_key="movements/movement-id/scontrino.pdf",
    )
    db.add_all([movement, receipt])
    db.flush()
    movement_id, receipt_id = movement.id, receipt.id

    response = delete_movement(movement_id, db, membership_of(alice, cassa))

    assert response.status_code == 204
    assert db.get(Movement, movement_id).deleted_at is not None
    assert db.get(MovementReceipt, receipt_id) is not None

    restored = restore_movement(movement_id, db, membership_of(alice, cassa))

    assert restored.restored is True
    assert db.get(Movement, movement_id).deleted_at is None
    assert [item.id for item in list_movements(db, cassa).items] == [movement_id]


def test_user_cannot_delete_another_users_movement(setup, membership_of) -> None:
    db, group, cassa, alice, bob = setup
    movement = make_movement(cassa, alice, "Supermercato", date.today(), datetime.now())
    db.add(movement)
    db.flush()

    with pytest.raises(HTTPException) as error:
        delete_movement(movement.id, db, membership_of(bob, cassa))

    assert error.value.status_code == 403
    assert db.get(Movement, movement.id) is not None
