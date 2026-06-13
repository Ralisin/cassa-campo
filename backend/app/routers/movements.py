import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import AdminUser, CurrentUser, DbSession, can_edit_movement
from app.models import Movement, MovementReimbursement
from app.schemas import MovementInput, MovementRead
from app.services import apply_movement_input, enforce_user_branch, movement_to_read

router = APIRouter(prefix="/movements", tags=["movements"])


def get_movement_or_404(db: DbSession, movement_id: uuid.UUID) -> Movement:
    movement = db.scalar(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
        )
        .where(Movement.id == movement_id)
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


@router.get("", response_model=list[MovementRead])
def list_movements(db: DbSession, _: CurrentUser) -> list[MovementRead]:
    movements = db.scalars(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
        )
        .order_by(Movement.operation_date.desc(), Movement.created_at.desc())
    ).all()
    return [movement_to_read(item) for item in movements]


@router.get("/{movement_id}", response_model=MovementRead)
def get_movement(movement_id: uuid.UUID, db: DbSession, _: CurrentUser) -> MovementRead:
    return movement_to_read(get_movement_or_404(db, movement_id))


@router.post("", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(data: MovementInput, db: DbSession, user: CurrentUser) -> MovementRead:
    enforce_user_branch(data, user)
    movement = Movement(created_by=user.id)
    apply_movement_input(movement, data)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement_to_read(get_movement_or_404(db, movement.id))


@router.put("/{movement_id}", response_model=MovementRead)
def update_movement(
    movement_id: uuid.UUID, data: MovementInput, db: DbSession, user: CurrentUser
) -> MovementRead:
    movement = get_movement_or_404(db, movement_id)
    if not can_edit_movement(user, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    enforce_user_branch(data, user)
    apply_movement_input(movement, data)
    db.commit()
    return movement_to_read(get_movement_or_404(db, movement.id))


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID, db: DbSession, _: AdminUser
) -> Response:
    db.delete(get_movement_or_404(db, movement_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
