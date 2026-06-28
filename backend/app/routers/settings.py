from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import CurrentCassa, DbSession, OperatorMembership
from app.models import CampCategoryBudget, CampSettings, ExpenseCategory
from app.schemas import SettingsInput, SettingsRead

router = APIRouter(prefix="/settings", tags=["settings"])


def latest_settings(db: DbSession, cassa_id) -> CampSettings | None:
    return db.scalar(
        select(CampSettings)
        .where(CampSettings.cassa_id == cassa_id)
        .order_by(CampSettings.created_at.desc())
        .limit(1)
    )


@router.get("", response_model=SettingsRead)
def get_settings(db: DbSession, cassa: CurrentCassa) -> SettingsRead:
    settings = latest_settings(db, cassa.id)
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured")
    return SettingsRead(
        **{
            field: getattr(settings, field)
            for field in SettingsRead.model_fields
            if field != "category_budgets"
        },
        category_budgets={item.category: item.amount for item in settings.category_budgets},
    )


@router.put("", response_model=SettingsRead)
def update_settings(
    data: SettingsInput, db: DbSession, operator: OperatorMembership
) -> SettingsRead:
    settings = latest_settings(db, operator.cassa_id) or CampSettings(cassa_id=operator.cassa_id)
    for field, value in data.model_dump(exclude={"category_budgets"}).items():
        setattr(settings, field, value)
    settings.max_budget = data.participants * data.quota_per_person
    settings.bank_initial = settings.max_budget - data.cash_initial
    db.add(settings)
    db.flush()
    categories = db.scalars(select(ExpenseCategory).where(ExpenseCategory.active.is_(True))).all()
    existing_budgets = {item.category: item for item in settings.category_budgets}
    for category in categories:
        budget = existing_budgets.get(category.slug)
        if budget is None:
            budget = CampCategoryBudget(settings_id=settings.id, category=category.slug)
            settings.category_budgets.append(budget)
        budget.amount = data.category_budgets.get(category.slug, 0)
    db.commit()
    db.refresh(settings)
    return SettingsRead(
        **{
            field: getattr(settings, field)
            for field in SettingsRead.model_fields
            if field != "category_budgets"
        },
        category_budgets={item.category: item.amount for item in settings.category_budgets},
    )
