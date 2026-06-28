from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Branch, MovementType, PaymentMethod
from app.schemas import MovementInput


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


def test_expense_category_is_required() -> None:
    with pytest.raises(ValidationError):
        MovementInput(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Fornitore",
            unit=Branch.GRUPPO,
            amount=Decimal("10.00"),
            notes="Spesa",
        )


def test_income_does_not_keep_an_expense_category() -> None:
    data = MovementInput(
        operation_date=date.today(),
        type=MovementType.INCOME,
        payment_method=PaymentMethod.CASH,
        supplier="Quota",
        unit=Branch.GRUPPO,
        category="vitto",
        amount=Decimal("10.00"),
        notes="Entrata",
    )
    assert data.category is None


def test_reimbursement_requires_cash_expense() -> None:
    with pytest.raises(ValidationError):
        MovementInput(
            operation_date=date.today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CARD,
            supplier="Fornitore",
            category="varie",
            amount=Decimal("10.00"),
            notes="Spesa",
            needs_reimbursement=True,
        )


def test_unit_is_optional_now_forced_by_cassa() -> None:
    # The unit is no longer chosen by the client; it may be omitted entirely.
    data = MovementInput(
        operation_date=date.today(),
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier="Fornitore",
        category="varie",
        amount=Decimal("10.00"),
        notes="Spesa",
    )
    assert data.unit is None
