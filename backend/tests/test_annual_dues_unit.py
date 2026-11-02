"""Focused annual dues tests that run without the PostgreSQL test service."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Cassa, CassaKind, CampSettings, Group, Membership, PaymentMethod, User, UserRole
from app.routers.exports import build_annual_excel_report
from app.routers.movements import create_movement, delete_movement, list_annual_dues, restore_movement, update_movement
from app.routers.settings import update_settings
from app.schemas import MovementInput, SettingsInput
from app.services import get_dashboard


@pytest.fixture
def annual_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        group = Group(slug="test", name="Test", email_domain="test.it")
        db.add(group)
        db.flush()
        cassa = Cassa(group_id=group.id, unit="E/G", kind=CassaKind.ANNO, year=2027)
        db.add(cassa)
        db.flush()
        user = User(email="admin@test.it", password_hash="x", name="Admin", group_id=group.id)
        db.add(user)
        db.flush()
        membership = Membership(user_id=user.id, cassa_id=cassa.id, role=UserRole.ADMIN)
        settings = CampSettings(cassa_id=cassa.id, camp_year=2027, camp_name="Anno", participants=2,
                                quota_per_person=Decimal("80"), max_budget=Decimal("160"),
                                cash_initial=Decimal("10"), bank_initial=Decimal("20"),
                                annual_balances_confirmed=True)
        db.add_all([membership, settings])
        db.commit()
        yield db, cassa, membership
    engine.dispose()


def dues(person, method=PaymentMethod.CASH):
    return MovementInput(operation_date=date(2026, 11, 2), type="entrata",
                         payment_method=method, supplier="Quota anno", amount=Decimal("80"),
                         notes=f"Quota per {person}", annual_dues_person=person)


def test_dues_count_balance_export_and_restore(annual_db):
    db, cassa, membership = annual_db
    first = create_movement(dues("Mario Rossi"), db, membership)
    second = create_movement(dues("Giulia Bianchi", PaymentMethod.BANK), db, membership)
    assert list_annual_dues(db, cassa)["paid"] == 2
    dashboard = get_dashboard(db, cassa.id)
    assert dashboard.cash_balance == Decimal("90")
    assert dashboard.bank_balance == Decimal("100")
    sheet = build_annual_excel_report(db, cassa).active
    assert sheet["E2"].value == 2
    assert sheet["E3"].value == 2
    assert sheet["A8"].value is None
    assert sheet["N2"].value == '=IF(OR(E3="",N1=""),"",E3*N1)'
    delete_movement(first.id, db, membership)
    assert list_annual_dues(db, cassa)["paid"] == 1
    restore_movement(first.id, db, membership)
    assert list_annual_dues(db, cassa)["paid"] == 2
    assert second.payment_method == PaymentMethod.BANK


def test_duplicate_and_capacity_are_rejected(annual_db):
    db, cassa, membership = annual_db
    create_movement(dues("Mario Rossi"), db, membership)
    with pytest.raises(HTTPException) as duplicate:
        create_movement(dues("  MARIO   ROSSI  "), db, membership)
    assert duplicate.value.status_code == 409
    create_movement(dues("Giulia Bianchi"), db, membership)
    with pytest.raises(HTTPException) as full:
        create_movement(dues("Luca Verdi"), db, membership)
    assert full.value.status_code == 422


def test_edit_and_restore_cannot_double_count(annual_db):
    db, cassa, membership = annual_db
    first = create_movement(dues("Mario Rossi"), db, membership)
    changed = update_movement(first.id, dues("Mario Rossi", PaymentMethod.BANK), db, membership)
    assert changed.payment_method == PaymentMethod.BANK
    assert get_dashboard(db, cassa.id).bank_balance == Decimal("100")
    delete_movement(first.id, db, membership)
    create_movement(dues("Mario Rossi"), db, membership)
    with pytest.raises(HTTPException) as conflict:
        restore_movement(first.id, db, membership)
    assert conflict.value.status_code == 409
    assert list_annual_dues(db, cassa)["paid"] == 1


def test_annual_settings_require_balance_review_and_preserve_headcount(annual_db):
    db, cassa, membership = annual_db
    settings = db.query(CampSettings).filter_by(cassa_id=cassa.id).one()
    settings.annual_balances_confirmed = False
    db.commit()
    with pytest.raises(HTTPException) as review:
        create_movement(dues("Mario Rossi"), db, membership)
    assert review.value.status_code == 422
    update_settings(SettingsInput(camp_year=2027, camp_name="Anno", participants=2,
                                  quota_per_person=Decimal("80"), cash_initial=Decimal("10"),
                                  bank_initial=Decimal("20"), confirm_annual_balances=True), db, membership)
    create_movement(dues("Mario Rossi"), db, membership)
    with pytest.raises(HTTPException) as capacity:
        update_settings(SettingsInput(camp_year=2027, camp_name="Anno", participants=0,
                                      quota_per_person=Decimal("80"), cash_initial=Decimal("10"),
                                      bank_initial=Decimal("20")), db, membership)
    assert capacity.value.status_code == 422
