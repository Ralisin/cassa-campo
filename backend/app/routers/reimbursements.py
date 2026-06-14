import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import AdminUser, CurrentUser, DbSession
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
    )


@router.get("", response_model=ReimbursementSummary)
def list_reimbursements(db: DbSession, user: CurrentUser) -> ReimbursementSummary:
    query = (
        select(Movement)
        .join(Movement.reimbursement)
        .options(*reimbursement_load_options())
        .order_by(Movement.operation_date.desc(), Movement.created_at.desc())
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Movement.created_by == user.id)
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
    admin: AdminUser,
) -> ReimbursementSummary:
    movement = get_movement_or_404(db, movement_id)
    if not movement.reimbursement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il movimento non richiede un rimborso",
        )
    was_reimbursed = movement.reimbursement.reimbursed_at is not None
    movement.reimbursement.reimbursed_at = datetime.now(UTC) if data.reimbursed else None
    movement.reimbursement.reimbursed_by = admin.id if data.reimbursed else None
    if data.reimbursed and not was_reimbursed and movement.created_by != admin.id:
        notify_reimbursement_completed(db, movement)
    db.commit()
    return list_reimbursements(db, admin)
