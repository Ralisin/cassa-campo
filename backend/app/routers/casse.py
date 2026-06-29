import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.audit_service import write_audit
from app.dependencies import CurrentUser, DbSession, OperatorMembership, WritableOperatorMembership
from app.models import Cassa, CassaStatus, Membership, UserRole
from app.schemas import CassaCreate, CassaRead
from app.services import cassa_to_read

router = APIRouter(prefix="/casse", tags=["casse"])


@router.get("", response_model=list[CassaRead])
def list_casse(db: DbSession, _user: CurrentUser, operator: OperatorMembership) -> list[CassaRead]:
    casse = db.scalars(
        select(Cassa)
        .where(Cassa.group_id == operator.cassa.group_id)
        .order_by(Cassa.unit, Cassa.kind, Cassa.year.desc())
    ).all()
    return [cassa_to_read(cassa) for cassa in casse]


@router.post("", response_model=CassaRead, status_code=status.HTTP_201_CREATED)
def create_cassa(
    data: CassaCreate, db: DbSession, user: CurrentUser, operator: OperatorMembership
) -> CassaRead:
    group_id = operator.cassa.group_id
    existing_open = db.scalar(
        select(Cassa).where(
            Cassa.group_id == group_id,
            Cassa.unit == data.unit.value,
            Cassa.kind == data.kind,
            Cassa.status == CassaStatus.OPEN,
        )
    )
    if existing_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esiste già una cassa aperta di questo tipo per questa unità",
        )
    cassa = Cassa(
        group_id=group_id,
        unit=data.unit.value,
        kind=data.kind,
        year=data.year,
        opened_at=data.opened_at or date.today(),
    )
    try:
        db.add(cassa)
        db.flush()
        db.add(Membership(user_id=user.id, cassa_id=cassa.id, role=operator.role))
        write_audit(
            db,
            action="cassa_created",
            entity_type="cassa",
            entity_id=cassa.id,
            cassa_id=operator.cassa_id,
            user_id=user.id,
            summary=f"Creata cassa {cassa.unit} {cassa.kind.value} {cassa.year}",
        )
        db.commit()
        db.refresh(cassa)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esiste già una cassa aperta o una cassa dello stesso tipo per questo anno",
        ) from exc
    return cassa_to_read(cassa)


@router.put("/{cassa_id}/close", response_model=CassaRead)
def close_cassa(
    cassa_id: uuid.UUID, db: DbSession, operator: WritableOperatorMembership
) -> CassaRead:
    cassa = db.scalar(
        select(Cassa).where(Cassa.id == cassa_id, Cassa.group_id == operator.cassa.group_id)
    )
    if not cassa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cassa not found")
    if not operator.user.is_system_admin:
        target_membership = db.scalar(
            select(Membership).where(
                Membership.user_id == operator.user_id,
                Membership.cassa_id == cassa.id,
            )
        )
        if target_membership is not None and target_membership.role not in (
            UserRole.ADMIN,
            UserRole.CASHIER,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or cashier role required on this cassa",
            )
    if cassa.status == CassaStatus.CLOSED:
        return cassa_to_read(cassa)
    cassa.status = CassaStatus.CLOSED
    cassa.closed_at = date.today()
    write_audit(
        db,
        action="cassa_closed",
        entity_type="cassa",
        entity_id=cassa.id,
        cassa_id=cassa.id,
        user_id=operator.user_id,
        summary=f"Chiusa cassa {cassa.unit} {cassa.kind.value} {cassa.year}",
    )
    db.commit()
    db.refresh(cassa)
    return cassa_to_read(cassa)
