from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession, OperatorUser
from app.models import CampSettings
from app.schemas import SettingsInput, SettingsRead

router = APIRouter(prefix="/settings", tags=["settings"])


def latest_settings(db: DbSession) -> CampSettings | None:
    return db.scalar(select(CampSettings).order_by(CampSettings.created_at.desc()).limit(1))


@router.get("", response_model=SettingsRead)
def get_settings(db: DbSession, _: CurrentUser) -> CampSettings:
    settings = latest_settings(db)
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured")
    return settings


@router.put("", response_model=SettingsRead)
def update_settings(data: SettingsInput, db: DbSession, _: OperatorUser) -> CampSettings:
    settings = latest_settings(db) or CampSettings()
    for field, value in data.model_dump().items():
        setattr(settings, field, value)
    settings.max_budget = data.participants * data.quota_per_person
    settings.bank_initial = settings.max_budget - data.cash_initial
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
