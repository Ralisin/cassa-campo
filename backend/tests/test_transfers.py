from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import CampSettings, TransferType, TreasuryTransfer, UserRole
from app.routers.transfers import create_transfer, delete_transfer, update_transfer
from app.schemas import TransferInput
from app.services import get_dashboard


@pytest.fixture
def setup(db, make_group, make_cassa, make_user, membership_of):
    group = make_group()
    cassa = make_cassa(group, "E/G")
    admin = make_user(group, "admin@roma108.it", memberships=[(cassa, UserRole.ADMIN)])
    return db, cassa, membership_of(admin, cassa)


def add_settings(db, cassa, *, participants=10, quota="100", cash="100", bank="500"):
    db.add(
        CampSettings(
            cassa_id=cassa.id,
            camp_year=2026,
            camp_name="Campo",
            participants=participants,
            quota_per_person=Decimal(quota),
            max_budget=Decimal(participants) * Decimal(quota),
            cash_initial=Decimal(cash),
            bank_initial=Decimal(bank),
        )
    )
    db.flush()


def test_transfer_moves_money_without_changing_budget(setup) -> None:
    db, cassa, admin = setup
    add_settings(db, cassa)

    create_transfer(
        TransferInput(
            operation_date=date.today(),
            type=TransferType.WITHDRAWAL,
            amount=Decimal("50"),
            notes="Prelievo cassa",
        ),
        db,
        admin,
    )
    dashboard = get_dashboard(db, cassa.id)
    assert dashboard.cash_balance == Decimal("150")
    assert dashboard.bank_balance == Decimal("850")
    assert dashboard.spent == Decimal("0")
    assert dashboard.remaining_budget == Decimal("1000")

    with pytest.raises(HTTPException):
        create_transfer(
            TransferInput(
                operation_date=date.today(),
                type=TransferType.DEPOSIT,
                amount=Decimal("200"),
                notes="Troppo contante",
            ),
            db,
            admin,
        )


def test_transfer_can_be_updated_and_deleted(setup) -> None:
    db, cassa, admin = setup
    add_settings(db, cassa, bank="900")

    created = create_transfer(
        TransferInput(
            operation_date=date.today(),
            type=TransferType.WITHDRAWAL,
            amount=Decimal("50"),
            notes="Prelievo cassa",
        ),
        db,
        admin,
    )
    updated = update_transfer(
        created.id,
        TransferInput(
            operation_date=date.today(),
            type=TransferType.DEPOSIT,
            amount=Decimal("25"),
            notes="Versamento corretto",
        ),
        db,
        admin,
    )

    dashboard = get_dashboard(db, cassa.id)
    assert updated.type == TransferType.DEPOSIT
    assert updated.notes == "Versamento corretto"
    assert dashboard.cash_balance == Decimal("75")
    assert dashboard.bank_balance == Decimal("925")

    response = delete_transfer(created.id, db, admin)

    assert response.status_code == 204
    assert db.get(TreasuryTransfer, created.id) is None
    dashboard = get_dashboard(db, cassa.id)
    assert dashboard.cash_balance == Decimal("100")
    assert dashboard.bank_balance == Decimal("900")


def test_transfer_update_validates_balance_without_counting_existing_transfer(setup) -> None:
    db, cassa, admin = setup
    add_settings(db, cassa, participants=1, quota="100", cash="0", bank="100")

    created = create_transfer(
        TransferInput(
            operation_date=date.today(),
            type=TransferType.WITHDRAWAL,
            amount=Decimal("100"),
            notes="Tutto",
        ),
        db,
        admin,
    )
    update_transfer(
        created.id,
        TransferInput(
            operation_date=date.today(),
            type=TransferType.WITHDRAWAL,
            amount=Decimal("100"),
            notes="Ancora tutto",
        ),
        db,
        admin,
    )

    with pytest.raises(HTTPException) as error:
        update_transfer(
            created.id,
            TransferInput(
                operation_date=date.today(),
                type=TransferType.WITHDRAWAL,
                amount=Decimal("101"),
                notes="Troppo",
            ),
            db,
            admin,
        )
    assert error.value.status_code == 400
