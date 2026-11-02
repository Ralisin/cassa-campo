import base64
import binascii
import json
import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from app.audit_service import write_audit
from app.dependencies import (
    CurrentCassa,
    DbSession,
    WritableMembership,
    can_edit_movement,
)
from app.models import (
    Cassa,
    CassaKind,
    CampSettings,
    Membership,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    User,
    UserRole,
)
from app.notification_service import notify_admins_of_movement
from app.schemas import (
    MovementCreatorRead,
    MovementInput,
    MovementPage,
    MovementRead,
    MovementRestoreResult,
)
from app.services import apply_movement_input, movement_to_read
from app.routers.settings import latest_settings

router = APIRouter(prefix="/movements", tags=["movements"])

PAGE_SIZE = 50


def validate_annual_dues(db: DbSession, cassa: Cassa, data: MovementInput,
                         movement_id: uuid.UUID | None = None) -> None:
    if not data.annual_dues_person:
        if data.payment_method == PaymentMethod.BANK:
            raise HTTPException(status_code=422, detail="Il bonifico è riservato alle quote anno")
        return
    if cassa.kind != CassaKind.ANNO:
        raise HTTPException(status_code=422, detail="Le quote anno si registrano solo nella cassa annuale")
    settings = db.scalar(select(CampSettings).where(CampSettings.cassa_id == cassa.id)
                         .order_by(CampSettings.created_at.desc()).limit(1).with_for_update())
    if not settings or settings.quota_per_person <= 0:
        raise HTTPException(status_code=422, detail="Imposta prima la quota per ragazzo")
    if not settings.annual_balances_confirmed:
        raise HTTPException(status_code=422, detail="Conferma prima i saldi iniziali nelle impostazioni")
    if data.amount != settings.quota_per_person:
        raise HTTPException(status_code=422, detail="L'importo deve corrispondere alla quota anno")
    key = " ".join(data.annual_dues_person.casefold().split())
    duplicate = db.scalar(select(Movement.id).where(
        Movement.cassa_id == cassa.id,
        Movement.annual_dues_person_key == key,
        Movement.deleted_at.is_(None),
        Movement.id != movement_id,
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="La quota di questo ragazzo risulta già pagata")
    paid = db.scalar(select(func.count(Movement.id)).where(
        Movement.cassa_id == cassa.id,
        Movement.annual_dues_person_key.is_not(None),
        Movement.deleted_at.is_(None),
        Movement.id != movement_id,
    )) or 0
    if paid >= settings.participants:
        raise HTTPException(status_code=422, detail="Le quote pagate raggiungono già il numero di ragazzi registrati")


def encode_cursor(movement: Movement) -> str:
    payload = json.dumps(
        [movement.operation_date.isoformat(), movement.created_at.isoformat(), str(movement.id)],
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[date, datetime, uuid.UUID]:
    try:
        payload = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        operation_date, created_at, movement_id = json.loads(payload)
        return date.fromisoformat(operation_date), datetime.fromisoformat(created_at), uuid.UUID(movement_id)
    except (binascii.Error, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid cursor") from exc


def get_movement_or_404(db: DbSession, movement_id: uuid.UUID, cassa_id: uuid.UUID) -> Movement:
    movement = db.scalar(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
            joinedload(Movement.performer),
            selectinload(Movement.receipts),
        )
        .where(Movement.id == movement_id, Movement.cassa_id == cassa_id)
        .where(Movement.deleted_at.is_(None))
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


def set_performer(db: DbSession, movement: Movement, requested_id: uuid.UUID | None,
                  membership: WritableMembership) -> None:
    if requested_id is None:
        if movement.performed_by_id is None:
            movement.performed_by_id = membership.user_id
        return
    if requested_id != membership.user_id:
        if membership.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        eligible = db.scalar(
            select(User.id)
            .join(Membership, Membership.user_id == User.id)
            .join(Cassa, Cassa.id == Membership.cassa_id)
            .where(
                User.id == requested_id,
                User.group_id == membership.cassa.group_id,
                User.deleted_at.is_(None),
                Cassa.group_id == membership.cassa.group_id,
                Cassa.unit == movement.unit,
            )
            .limit(1)
        )
        if eligible is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La persona selezionata non appartiene all'unità del movimento",
            )
    movement.performed_by_id = requested_id


@router.get("", response_model=MovementPage)
def list_movements(
    db: DbSession,
    cassa: CurrentCassa,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = PAGE_SIZE,
    query: Annotated[str | None, Query(max_length=255)] = None,
    movement_type: MovementType | None = None,
    payment_method: PaymentMethod | None = None,
    creator: uuid.UUID | None = None,
    reimbursement: Annotated[str | None, Query(pattern="^(da_rimborsare|rimborsato|nessuno)$")] = None,
) -> MovementPage:
    filters = [Movement.cassa_id == cassa.id, Movement.deleted_at.is_(None)]
    if query and (term := query.strip()):
        pattern = f"%{term}%"
        filters.append(
            or_(
                Movement.supplier.ilike(pattern),
                Movement.annual_dues_person.ilike(pattern),
                Movement.notes.ilike(pattern),
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    if movement_type:
        filters.append(Movement.type == movement_type)
    if payment_method:
        filters.append(Movement.payment_method == payment_method)
    if creator:
        filters.append(Movement.created_by == creator)
    if reimbursement == "nessuno":
        filters.append(MovementReimbursement.id.is_(None))
    elif reimbursement == "da_rimborsare":
        filters.extend(
            [MovementReimbursement.id.is_not(None), MovementReimbursement.reimbursed_at.is_(None)]
        )
    elif reimbursement == "rimborsato":
        filters.append(MovementReimbursement.reimbursed_at.is_not(None))

    base_query = (
        select(Movement)
        .join(Movement.creator)
        .outerjoin(Movement.reimbursement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
            joinedload(Movement.performer),
            selectinload(Movement.receipts),
        )
        .where(*filters)
    )
    total = db.scalar(
        select(func.count(Movement.id))
        .join(Movement.creator)
        .outerjoin(Movement.reimbursement)
        .where(*filters)
    ) or 0
    if cursor:
        cursor_date, cursor_created_at, cursor_id = decode_cursor(cursor)
        base_query = base_query.where(
            or_(
                Movement.operation_date < cursor_date,
                and_(
                    Movement.operation_date == cursor_date,
                    Movement.created_at < cursor_created_at,
                ),
                and_(
                    Movement.operation_date == cursor_date,
                    Movement.created_at == cursor_created_at,
                    Movement.id < cursor_id,
                ),
            )
        )
    movements = db.scalars(
        base_query
        .order_by(Movement.operation_date.desc(), Movement.created_at.desc(), Movement.id.desc())
        .limit(limit + 1)
    ).unique().all()
    has_more = len(movements) > limit
    movements = movements[:limit]
    creators = db.execute(
        select(User.id, User.name)
        .join(Movement, Movement.created_by == User.id)
        .where(Movement.cassa_id == cassa.id)
        .where(Movement.deleted_at.is_(None))
        .distinct()
        .order_by(User.name)
    ).all()
    return MovementPage(
        items=[movement_to_read(item) for item in movements],
        next_cursor=encode_cursor(movements[-1]) if has_more else None,
        total=total,
        creators=[MovementCreatorRead(id=item.id, name=item.name) for item in creators],
    )


@router.get("/deleted", response_model=list[MovementRead])
def list_deleted_movements(db: DbSession, membership: WritableMembership) -> list[MovementRead]:
    movements = db.scalars(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
            joinedload(Movement.performer),
            selectinload(Movement.receipts),
        )
        .where(Movement.cassa_id == membership.cassa_id, Movement.deleted_at.is_not(None))
        .order_by(Movement.deleted_at.desc(), Movement.created_at.desc())
        .limit(100)
    ).unique().all()
    return [movement_to_read(item) for item in movements]


@router.get("/annual-dues")
def list_annual_dues(db: DbSession, cassa: CurrentCassa) -> dict:
    if cassa.kind != CassaKind.ANNO:
        raise HTTPException(status_code=404, detail="Disponibile solo per la cassa annuale")
    settings = latest_settings(db, cassa.id)
    payments = db.scalars(select(Movement).where(
        Movement.cassa_id == cassa.id,
        Movement.annual_dues_person_key.is_not(None),
        Movement.deleted_at.is_(None),
    ).order_by(Movement.annual_dues_person, Movement.operation_date)).all()
    return {
        "paid": len(payments),
        "registered": settings.participants if settings else 0,
        "quota_per_person": settings.quota_per_person if settings else 0,
        "payments": [{
            "movement_id": item.id,
            "person": item.annual_dues_person,
            "operation_date": item.operation_date,
            "amount": item.amount,
            "payment_method": item.payment_method,
        } for item in payments],
    }


@router.get("/{movement_id}", response_model=MovementRead)
def get_movement(movement_id: uuid.UUID, db: DbSession, cassa: CurrentCassa) -> MovementRead:
    return movement_to_read(get_movement_or_404(db, movement_id, cassa.id))


@router.post("", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(data: MovementInput, db: DbSession, membership: WritableMembership) -> MovementRead:
    cassa = membership.cassa
    validate_annual_dues(db, cassa, data)
    movement = Movement(created_by=membership.user_id)
    apply_movement_input(movement, data, cassa, membership.role)
    set_performer(db, movement, data.performed_by_id, membership)
    db.add(movement)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if not data.annual_dues_person:
            raise
        raise HTTPException(status_code=409, detail="La quota di questo ragazzo risulta già pagata") from exc
    notify_admins_of_movement(
        db,
        movement,
        membership.user,
        reimbursement_requested=data.needs_reimbursement,
    )
    write_audit(
        db,
        action="movement_created",
        entity_type="movement",
        entity_id=movement.id,
        cassa_id=cassa.id,
        user_id=membership.user_id,
        summary=f"Creato movimento {movement.supplier} da € {movement.amount}",
        details={"supplier": movement.supplier, "amount": str(movement.amount)},
    )
    db.commit()
    db.refresh(movement)
    return movement_to_read(get_movement_or_404(db, movement.id, cassa.id))


@router.put("/{movement_id}", response_model=MovementRead)
def update_movement(
    movement_id: uuid.UUID, data: MovementInput, db: DbSession, membership: WritableMembership
) -> MovementRead:
    cassa = membership.cassa
    movement = get_movement_or_404(db, movement_id, cassa.id)
    if not can_edit_movement(membership, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    validate_annual_dues(db, cassa, data, movement_id)
    reimbursement_requested = movement.reimbursement is None and data.needs_reimbursement
    apply_movement_input(movement, data, cassa, membership.role)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if not data.annual_dues_person:
            raise
        raise HTTPException(status_code=409, detail="La quota di questo ragazzo risulta già pagata") from exc
    set_performer(db, movement, data.performed_by_id, membership)
    if reimbursement_requested:
        notify_admins_of_movement(db, movement, membership.user, reimbursement_requested=True)
    write_audit(
        db,
        action="movement_updated",
        entity_type="movement",
        entity_id=movement.id,
        cassa_id=cassa.id,
        user_id=membership.user_id,
        summary=f"Modificato movimento {movement.supplier}",
        details={"supplier": movement.supplier, "amount": str(movement.amount)},
    )
    db.commit()
    return movement_to_read(get_movement_or_404(db, movement.id, cassa.id))


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID, db: DbSession, membership: WritableMembership
) -> Response:
    movement = get_movement_or_404(db, movement_id, membership.cassa_id)
    if not can_edit_movement(membership, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    movement.deleted_at = datetime.now(UTC)
    movement.deleted_by = membership.user_id
    write_audit(
        db,
        action="movement_deleted",
        entity_type="movement",
        entity_id=movement.id,
        cassa_id=membership.cassa_id,
        user_id=membership.user_id,
        summary=f"Spostato nel cestino movimento {movement.supplier}",
        details={"supplier": movement.supplier, "amount": str(movement.amount)},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{movement_id}/restore", response_model=MovementRestoreResult)
def restore_movement(
    movement_id: uuid.UUID, db: DbSession, membership: WritableMembership
) -> MovementRestoreResult:
    movement = db.scalar(
        select(Movement).where(
            Movement.id == movement_id,
            Movement.cassa_id == membership.cassa_id,
            Movement.deleted_at.is_not(None),
        )
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    if not can_edit_movement(membership, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if movement.annual_dues_person_key:
        duplicate = db.scalar(select(Movement.id).where(
            Movement.cassa_id == membership.cassa_id,
            Movement.annual_dues_person_key == movement.annual_dues_person_key,
            Movement.deleted_at.is_(None),
            Movement.id != movement.id,
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail="Esiste già una quota attiva per questo ragazzo")
        settings = db.scalar(select(CampSettings).where(CampSettings.cassa_id == membership.cassa_id)
                             .order_by(CampSettings.created_at.desc()).limit(1).with_for_update())
        paid = db.scalar(select(func.count(Movement.id)).where(
            Movement.cassa_id == membership.cassa_id,
            Movement.annual_dues_person_key.is_not(None),
            Movement.deleted_at.is_(None),
        )) or 0
        if settings and paid >= settings.participants:
            raise HTTPException(status_code=422, detail="Non ci sono posti disponibili tra i ragazzi registrati")
    movement.deleted_at = None
    movement.deleted_by = None
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esiste già una quota attiva per questo ragazzo") from exc
    write_audit(
        db,
        action="movement_restored",
        entity_type="movement",
        entity_id=movement.id,
        cassa_id=membership.cassa_id,
        user_id=membership.user_id,
        summary=f"Ripristinato movimento {movement.supplier}",
    )
    db.commit()
    return MovementRestoreResult(id=movement.id)
