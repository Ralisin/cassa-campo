from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Branch, MovementType, PaymentMethod, User, UserRole
from app.schemas import MovementInput
from app.services import enforce_user_branch


def test_movement_notes_are_required() -> None:
    with pytest.raises(ValidationError):
        MovementInput(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Fornitore",
            unit="Gruppo",
            amount=Decimal("10.00"),
            notes="",
        )


def movement_input(unit: Branch = Branch.GRUPPO) -> MovementInput:
    return MovementInput(
        operation_date=date.today(),
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier="Fornitore",
        unit=unit,
        amount=Decimal("10.00"),
        notes="Spesa",
    )


def test_user_movement_is_forced_to_profile_branch() -> None:
    data = movement_input()
    user = User(
        email="utente@example.it",
        name="Utente",
        password_hash="unused",
        role=UserRole.USER,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )

    enforce_user_branch(data, user)

    assert data.unit == Branch.ESPLORATORI_GUIDE


def test_admin_can_choose_movement_branch() -> None:
    data = movement_input()
    admin = User(
        email="admin@example.it",
        name="Admin",
        password_hash="unused",
        role=UserRole.ADMIN,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )

    enforce_user_branch(data, admin)

    assert data.unit == Branch.GRUPPO
