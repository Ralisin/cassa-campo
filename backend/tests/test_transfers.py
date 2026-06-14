import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Branch, CampSettings, TransferType, TreasuryTransfer, User, UserRole
from app.routers.transfers import create_transfer, delete_transfer, update_transfer
from app.schemas import TransferInput
from app.services import get_dashboard


def test_transfer_moves_money_without_changing_budget() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.it",
            name="Admin",
            password_hash="unused",
            role=UserRole.ADMIN,
            branch=Branch.ESPLORATORI_GUIDE.value,
        )
        db.add(admin)
        db.add(
            CampSettings(
                camp_year=2026,
                camp_name="Campo",
                participants=10,
                quota_per_person=Decimal("100"),
                max_budget=Decimal("1000"),
                cash_initial=Decimal("100"),
                bank_initial=Decimal("500"),
            )
        )
        db.commit()

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
        dashboard = get_dashboard(db)

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


def test_transfer_can_be_updated_and_deleted() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.it",
            name="Admin",
            password_hash="unused",
            role=UserRole.ADMIN,
            branch=Branch.ESPLORATORI_GUIDE.value,
        )
        db.add_all(
            [
                admin,
                CampSettings(
                    camp_year=2026,
                    camp_name="Campo",
                    participants=10,
                    quota_per_person=Decimal("100"),
                    max_budget=Decimal("1000"),
                    cash_initial=Decimal("100"),
                    bank_initial=Decimal("900"),
                ),
            ]
        )
        db.commit()

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

        dashboard = get_dashboard(db)
        assert updated.type == TransferType.DEPOSIT
        assert updated.notes == "Versamento corretto"
        assert dashboard.cash_balance == Decimal("75")
        assert dashboard.bank_balance == Decimal("925")

        response = delete_transfer(created.id, db, admin)

        assert response.status_code == 204
        assert db.get(TreasuryTransfer, created.id) is None
        dashboard = get_dashboard(db)
        assert dashboard.cash_balance == Decimal("100")
        assert dashboard.bank_balance == Decimal("900")


def test_transfer_update_validates_balance_without_counting_existing_transfer() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.it",
            name="Admin",
            password_hash="unused",
            role=UserRole.ADMIN,
            branch=Branch.ESPLORATORI_GUIDE.value,
        )
        db.add_all(
            [
                admin,
                CampSettings(
                    camp_year=2026,
                    camp_name="Campo",
                    participants=1,
                    quota_per_person=Decimal("100"),
                    max_budget=Decimal("100"),
                    cash_initial=Decimal("0"),
                    bank_initial=Decimal("100"),
                ),
            ]
        )
        db.commit()
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
