from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import AdminMembership, CurrentUser, DbSession
from app.models import Cassa
from app.schemas import CassaCreate, CassaRead

router = APIRouter(prefix="/casse", tags=["casse"])


@router.get("", response_model=list[CassaRead])
def list_casse(db: DbSession, user: CurrentUser, _: AdminMembership) -> list[Cassa]:
    return list(
        db.scalars(
            select(Cassa).where(Cassa.group_id == user.group_id).order_by(Cassa.unit)
        ).all()
    )


@router.post("", response_model=CassaRead, status_code=status.HTTP_201_CREATED)
def create_cassa(
    data: CassaCreate, db: DbSession, user: CurrentUser, _: AdminMembership
) -> Cassa:
    cassa = Cassa(group_id=user.group_id, unit=data.unit.value)
    try:
        db.add(cassa)
        db.commit()
        db.refresh(cassa)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cassa per questa unità esiste già",
        ) from exc
    return cassa
