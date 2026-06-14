from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import ExpenseCategory, User, UserRole
from app.routers.settings import get_settings, update_settings
from app.schemas import SettingsInput


def test_category_budgets_are_saved_with_settings() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        admin = User(
            email="admin@example.it",
            name="Admin",
            password_hash="unused",
            role=UserRole.ADMIN,
            branch="E/G",
        )
        db.add_all(
            [
                admin,
                ExpenseCategory(slug="vitto", label="Vitto", position=1),
                ExpenseCategory(slug="alloggio", label="Alloggio", position=2),
                ExpenseCategory(slug="trasporti", label="Trasporti", position=3),
                ExpenseCategory(slug="varie", label="Varie", position=4),
            ]
        )
        db.commit()

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
            admin,
        )
        settings = get_settings(db, admin)

    assert settings.category_budgets == {
        "vitto": Decimal("700.00"),
        "alloggio": Decimal("500.00"),
        "trasporti": Decimal("300.00"),
        "varie": Decimal("200.00"),
    }
