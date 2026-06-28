from decimal import Decimal

from app.models import UserRole
from app.routers.settings import get_settings, update_settings
from app.schemas import SettingsInput


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
