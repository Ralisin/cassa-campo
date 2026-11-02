from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.audit_service import write_audit
from app.dependencies import CurrentCassa, DbSession, WritableOperatorMembership
from app.models import CampCategoryBudget, CampSettings, CassaKind, ExpenseCategory, Movement
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
        category_budgets=(
            {} if cassa.kind == CassaKind.ANNO
            else {item.category: item.amount for item in settings.category_budgets}
        ),
    )


@router.put("", response_model=SettingsRead)
def update_settings(
    data: SettingsInput, db: DbSession, operator: WritableOperatorMembership
) -> SettingsRead:
    if operator.cassa.kind == CassaKind.CAMPO and data.cash_initial > data.participants * data.quota_per_person:
        raise HTTPException(status_code=422, detail="Initial cash cannot exceed the camp budget")
    settings = (
        db.scalar(select(CampSettings).where(CampSettings.cassa_id == operator.cassa_id)
                  .order_by(CampSettings.created_at.desc()).limit(1).with_for_update())
        if operator.cassa.kind == CassaKind.ANNO else latest_settings(db, operator.cassa_id)
    ) or CampSettings(cassa_id=operator.cassa_id)
    if operator.cassa.kind == CassaKind.ANNO:
        paid = db.scalar(select(func.count(Movement.id)).where(
            Movement.cassa_id == operator.cassa_id,
            Movement.annual_dues_person_key.is_not(None),
            Movement.deleted_at.is_(None),
        )) or 0
        if data.participants < paid:
            raise HTTPException(status_code=422, detail="I ragazzi registrati non possono essere meno delle quote pagate")
        if paid and settings.quota_per_person != data.quota_per_person:
            raise HTTPException(status_code=422, detail="La quota per ragazzo non può cambiare dopo i pagamenti")
    for field, value in data.model_dump(exclude={"category_budgets", "bank_initial", "confirm_annual_balances"}).items():
        setattr(settings, field, value)
    settings.max_budget = data.participants * data.quota_per_person
    if operator.cassa.kind == CassaKind.ANNO:
        settings.bank_initial = data.bank_initial if data.bank_initial is not None else (settings.bank_initial or 0)
        if data.confirm_annual_balances:
            if data.bank_initial is None:
                raise HTTPException(status_code=422, detail="Inserisci il saldo iniziale della banca")
            settings.annual_balances_confirmed = True
    else:
        settings.bank_initial = settings.max_budget - data.cash_initial
    db.add(settings)
    db.flush()
    if operator.cassa.kind == CassaKind.ANNO:
        for budget in settings.category_budgets:
            budget.amount = 0
    else:
        categories = db.scalars(select(ExpenseCategory).where(ExpenseCategory.active.is_(True))).all()
        existing_budgets = {item.category: item for item in settings.category_budgets}
        for category in categories:
            budget = existing_budgets.get(category.slug)
            if budget is None:
                budget = CampCategoryBudget(settings_id=settings.id, category=category.slug)
                settings.category_budgets.append(budget)
            budget.amount = data.category_budgets.get(category.slug, 0)
    write_audit(
        db,
        action="settings_updated",
        entity_type="settings",
        entity_id=settings.id,
        cassa_id=operator.cassa_id,
        user_id=operator.user_id,
        summary=f"Aggiornate impostazioni {settings.camp_name}",
        details={"camp_year": settings.camp_year, "participants": settings.participants},
    )
    db.commit()
    db.refresh(settings)
    return SettingsRead(
        **{
            field: getattr(settings, field)
            for field in SettingsRead.model_fields
            if field != "category_budgets"
        },
        category_budgets=(
            {} if operator.cassa.kind == CassaKind.ANNO
            else {item.category: item.amount for item in settings.category_budgets}
        ),
    )
