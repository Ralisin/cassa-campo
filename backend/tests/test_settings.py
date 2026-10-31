from decimal import Decimal

from app.models import Cassa, CassaKind, CampCategoryBudget, Movement, MovementType, PaymentMethod, UserRole
from app.routers.settings import get_settings, update_settings
from app.schemas import SettingsInput
from app.services import get_dashboard
from app.services import camp_today


def test_category_budgets_are_saved_with_settings(
    db, make_group, make_cassa, make_user, membership_of
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    admin = make_user(group, "admin@roma108.it", memberships=[(cassa, UserRole.ADMIN)])
    membership = membership_of(admin, cassa)

    update_settings(
        SettingsInput(
            camp_year=2026,
            camp_name="Campo",
            participants=20,
            quota_per_person=Decimal("100"),
            cash_initial=Decimal("500"),
            category_budgets={
                "vitto": Decimal("700"),
                "alloggio": Decimal("500"),
                "trasporti": Decimal("300"),
                "varie": Decimal("200"),
            },
        ),
        db,
        membership,
    )
    settings = get_settings(db, cassa)

    assert settings.category_budgets == {
        "vitto": Decimal("700.00"),
        "alloggio": Decimal("500.00"),
        "trasporti": Decimal("300.00"),
        "varie": Decimal("200.00"),
    }


def test_annual_cassa_keeps_spending_statistics_without_category_budgets(
    db, make_group, make_user, membership_of
) -> None:
    group = make_group()
    cassa = Cassa(group_id=group.id, unit="E/G", kind=CassaKind.ANNO, year=2027)
    db.add(cassa)
    db.flush()
    admin = make_user(group, "admin@roma108.it", memberships=[(cassa, UserRole.ADMIN)])
    membership = membership_of(admin, cassa)

    saved = update_settings(
        SettingsInput(
            camp_year=2027,
            camp_name="Anno scout",
            participants=0,
            quota_per_person=Decimal("0"),
            cash_initial=Decimal("0"),
            category_budgets={"vitto": Decimal("300")},
        ),
        db,
        membership,
    )
    assert saved.category_budgets == {}
    assert get_settings(db, cassa).category_budgets == {}

    db.add(
        Movement(
            cassa_id=cassa.id,
            operation_date=camp_today(),
            type=MovementType.EXPENSE,
            payment_method=PaymentMethod.CASH,
            supplier="Spesa anno scout",
            unit="E/G",
            category="vitto",
            amount=Decimal("42.00"),
            created_by=admin.id,
        )
    )
    db.flush()
    dashboard = get_dashboard(db, cassa.id)
    vitto = next(item for item in dashboard.category_summaries if item.category == "vitto")
    assert vitto.spent == Decimal("42.00")
    assert vitto.budget == Decimal("0.00")
    assert all(anomaly.kind != "over_budget" for anomaly in dashboard.anomalies)

    # A legacy annual budget is also ignored until the next settings save clears it.
    settings_id = get_settings(db, cassa).id
    legacy = CampCategoryBudget(settings_id=settings_id, category="vitto", amount=Decimal("10"))
    db.add(legacy)
    db.flush()
    assert get_dashboard(db, cassa.id).category_summaries[0].budget == Decimal("0.00")
