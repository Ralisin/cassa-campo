import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.dependencies import CurrentMembership, DbSession, OperatorMembership
from app.models import Movement, MovementReimbursement, UserRole
from app.notification_service import notify_reimbursement_completed
from app.routers.movements import get_movement_or_404
from app.schemas import ReimbursementSummary, ReimbursementUpdate
from app.services import movement_to_read

router = APIRouter(prefix="/reimbursements", tags=["reimbursements"])
ZERO = Decimal("0.00")


def reimbursement_load_options():
    return (
        joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
        joinedload(Movement.creator),
        selectinload(Movement.receipts),
    )


@router.get("", response_model=ReimbursementSummary)
def list_reimbursements(db: DbSession, membership: CurrentMembership) -> ReimbursementSummary:
    query = (
        select(Movement)
        .join(Movement.reimbursement)
        .options(*reimbursement_load_options())
        .where(Movement.cassa_id == membership.cassa_id)
        .order_by(Movement.operation_date.desc(), Movement.created_at.desc())
    )
    if membership.role not in (UserRole.ADMIN, UserRole.CASHIER):
        query = query.where(Movement.created_by == membership.user_id)
    movements = list(db.scalars(query).unique().all())
    pending = [movement for movement in movements if not movement.reimbursement.reimbursed_at]
    reimbursed = [movement for movement in movements if movement.reimbursement.reimbursed_at]
    return ReimbursementSummary(
        pending_amount=sum((movement.amount for movement in pending), ZERO),
        reimbursed_amount=sum((movement.amount for movement in reimbursed), ZERO),
        pending_count=len(pending),
        reimbursed_count=len(reimbursed),
        movements=[movement_to_read(movement) for movement in movements],
    )


@router.put("/{movement_id}", response_model=ReimbursementSummary)
def update_reimbursement(
    movement_id: uuid.UUID,
    data: ReimbursementUpdate,
    db: DbSession,
    operator: OperatorMembership,
) -> ReimbursementSummary:
    movement = get_movement_or_404(db, movement_id, operator.cassa_id)
    if not movement.reimbursement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il movimento non richiede un rimborso",
        )
    was_reimbursed = movement.reimbursement.reimbursed_at is not None
    movement.reimbursement.reimbursed_at = datetime.now(UTC) if data.reimbursed else None
    movement.reimbursement.reimbursed_by = operator.user_id if data.reimbursed else None
    if data.reimbursed and not was_reimbursed and movement.created_by != operator.user_id:
        notify_reimbursement_completed(db, movement)
    db.commit()
    return list_reimbursements(db, operator)
