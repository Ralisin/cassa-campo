import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    BalanceType,
    Branch,
    CampSettings,
    Movement,
    MovementType,
    PaymentMethod,
    TransferType,
    TreasuryTransfer,
    User,
    UserRole,
)
from app.routers.exports import build_excel_report


def test_excel_report_matches_camp_layout_and_includes_transfers() -> None:
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
                camp_name="Campo Estivo",
                participants=38,
                quota_per_person=Decimal("200"),
                max_budget=Decimal("7600"),
                cash_initial=Decimal("1000"),
                bank_initial=Decimal("6600"),
            )
        )
        db.flush()
        db.add(
            Movement(
                created_at=datetime(2026, 7, 27, 10),
                operation_date=date(2026, 7, 24),
                type=MovementType.EXPENSE,
                payment_method=PaymentMethod.CASH,
                supplier="Macellaio",
                unit=Branch.ESPLORATORI_GUIDE.value,
                balance_type=BalanceType.CAMP,
                amount=Decimal("12"),
                notes="Acquisto carne",
                created_by=admin.id,
            )
        )
        db.add(
            TreasuryTransfer(
                created_at=datetime(2026, 7, 28, 10),
                operation_date=date(2026, 7, 25),
                type=TransferType.WITHDRAWAL,
                amount=Decimal("100"),
                notes="Prelievo ATM",
                created_by=admin.id,
            )
        )
        db.commit()

        workbook = build_excel_report(db)
        sheet = workbook["Bilancio Campo 2026"]

    assert sheet["E2"].value == 38
    assert sheet.sheet_view.showGridLines
    assert {
        "A4:C5",
        "A6:A7",
        "B6:B7",
        "C6:C7",
        "D6:D7",
        "E4:E7",
        "F4:F7",
        "G4:I7",
        "J4:L5",
        "M4:O5",
        "P4:P7",
    }.issubset({str(range_) for range_ in sheet.merged_cells.ranges})
    assert sheet["E3"].value == 200
    assert sheet["L2"].value == "=E2*E3"
    assert sheet["L7"].value == 1000
    assert sheet["O7"].value == "=L2-L7"
    assert sheet["D8"].value == "Macellaio"
    assert sheet["F8"].value == "C"
    assert sheet["K8"].value == 12
    assert sheet["D9"].value == "Giroconto"
    assert sheet["F9"].value == "C"
    assert sheet["J9"].value == 100
    assert sheet["N9"].value == 100
    validations = {
        (validation.formula1, str(next(iter(validation.cells.ranges))))
        for validation in sheet.data_validations.dataValidation
    }
    assert ('"L/C,E/G,R/S,CoCa,Gruppo"', "E8:E500") in validations
    assert ('"O,C,A"', "F8:F500") in validations
