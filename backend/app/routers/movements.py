import base64
import binascii
import json
import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.dependencies import (
    CurrentCassa,
    CurrentMembership,
    DbSession,
    WritableMembership,
    can_edit_movement,
)
from app.models import Movement, MovementReimbursement, MovementType, PaymentMethod, User
from app.notification_service import notify_admins_of_movement
from app.receipt_storage import get_receipt_storage
from app.schemas import MovementCreatorRead, MovementInput, MovementPage, MovementRead
from app.services import apply_movement_input, movement_to_read

router = APIRouter(prefix="/movements", tags=["movements"])

PAGE_SIZE = 50


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
            selectinload(Movement.receipts),
        )
        .where(Movement.id == movement_id, Movement.cassa_id == cassa_id)
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


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
    filters = [Movement.cassa_id == cassa.id]
    if query and (term := query.strip()):
        pattern = f"%{term}%"
        filters.append(
            or_(
                Movement.supplier.ilike(pattern),
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
        .distinct()
        .order_by(User.name)
    ).all()
    return MovementPage(
        items=[movement_to_read(item) for item in movements],
        next_cursor=encode_cursor(movements[-1]) if has_more else None,
        total=total,
        creators=[MovementCreatorRead(id=item.id, name=item.name) for item in creators],
    )


@router.get("/{movement_id}", response_model=MovementRead)
def get_movement(movement_id: uuid.UUID, db: DbSession, cassa: CurrentCassa) -> MovementRead:
    return movement_to_read(get_movement_or_404(db, movement_id, cassa.id))


@router.post("", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(data: MovementInput, db: DbSession, membership: WritableMembership) -> MovementRead:
    cassa = membership.cassa
    movement = Movement(created_by=membership.user_id)
    apply_movement_input(movement, data, cassa)
    db.add(movement)
    db.flush()
    notify_admins_of_movement(
        db,
        movement,
        membership.user,
        reimbursement_requested=data.needs_reimbursement,
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
    reimbursement_requested = movement.reimbursement is None and data.needs_reimbursement
    apply_movement_input(movement, data, cassa)
    if reimbursement_requested:
        notify_admins_of_movement(db, movement, membership.user, reimbursement_requested=True)
    db.commit()
    return movement_to_read(get_movement_or_404(db, movement.id, cassa.id))


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID, db: DbSession, membership: WritableMembership
) -> Response:
    movement = get_movement_or_404(db, movement_id, membership.cassa_id)
    if not can_edit_movement(membership, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if movement.receipts:
        storage = get_receipt_storage()
        for receipt in movement.receipts:
            storage.delete(receipt.storage_key)
    db.delete(movement)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
