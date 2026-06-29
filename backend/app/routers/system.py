import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.dependencies import DbSession, SystemAdmin
from app.models import Cassa, CassaStatus, Group, Movement, MovementReceipt, User
from app.receipt_storage import get_receipt_storage
from app.schemas import SystemCassaRead, SystemGroupRead, SystemOverview
from app.services import get_dashboard

router = APIRouter(prefix="/system", tags=["system"])


def system_domain() -> str:
    return settings.system_admin_email.strip().lower().split("@")[-1]


def get_group_or_404(db: DbSession, group_id: uuid.UUID) -> Group:
    group = db.scalar(
        select(Group)
        .where(Group.id == group_id, Group.email_domain != system_domain())
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


def get_cassa_or_404(db: DbSession, cassa_id: uuid.UUID) -> Cassa:
    cassa = db.scalar(
        select(Cassa)
        .join(Cassa.group)
        .where(Cassa.id == cassa_id, Group.email_domain != system_domain())
    )
    if not cassa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cassa not found")
    return cassa


def delete_receipt_objects(db: DbSession, group_id: uuid.UUID) -> None:
    receipts = db.scalars(
        select(MovementReceipt)
        .join(MovementReceipt.movement)
        .join(Cassa, Cassa.id == Movement.cassa_id)
        .where(Cassa.group_id == group_id)
    ).all()
    if not receipts:
        return
    storage = get_receipt_storage()
    for receipt in receipts:
        storage.delete(receipt.storage_key)


def delete_cassa_receipt_objects(db: DbSession, cassa_id: uuid.UUID) -> None:
    receipts = db.scalars(
        select(MovementReceipt)
        .join(MovementReceipt.movement)
        .where(Movement.cassa_id == cassa_id)
    ).all()
    if not receipts:
        return
    storage = get_receipt_storage()
    for receipt in receipts:
        storage.delete(receipt.storage_key)


def system_cassa_to_read(
    db: DbSession, cassa: Cassa, movement_counts: dict[uuid.UUID, int]
) -> SystemCassaRead:
    dashboard = get_dashboard(db, cassa.id)
    return SystemCassaRead(
        id=cassa.id,
        group_id=cassa.group_id,
        unit=cassa.unit,
        kind=cassa.kind,
        status=cassa.status,
        year=cassa.year,
        opened_at=cassa.opened_at,
        closed_at=cassa.closed_at,
        is_closed=cassa.status == CassaStatus.CLOSED,
        created_at=cassa.created_at,
        movements_count=movement_counts.get(cassa.id, 0),
        cash_balance=dashboard.cash_balance,
        bank_balance=dashboard.bank_balance,
    )


@router.get("/overview", response_model=SystemOverview)
def overview(db: DbSession, _: SystemAdmin) -> SystemOverview:
    groups = db.scalars(
        select(Group)
        .options(selectinload(Group.casse))
        .where(Group.email_domain != system_domain())
        .order_by(Group.name, Group.slug)
    ).all()
    user_counts = dict(
        db.execute(
            select(User.group_id, func.count(User.id))
            .where(User.is_system_admin.is_(False))
            .group_by(User.group_id)
        ).all()
    )
    movement_counts = dict(
        db.execute(select(Movement.cassa_id, func.count(Movement.id)).group_by(Movement.cassa_id)).all()
    )

    return SystemOverview(
        groups=[
            SystemGroupRead(
                id=group.id,
                slug=group.slug,
                name=group.name,
                email_domain=group.email_domain,
                created_at=group.created_at,
                users_count=user_counts.get(group.id, 0),
                casse=[system_cassa_to_read(db, cassa, movement_counts) for cassa in sorted(group.casse, key=lambda item: item.unit)],
            )
            for group in groups
        ]
    )


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: uuid.UUID, db: DbSession, _: SystemAdmin) -> Response:
    group = get_group_or_404(db, group_id)
    delete_receipt_objects(db, group.id)
    db.execute(delete(Cassa).where(Cassa.group_id == group.id))
    db.execute(delete(User).where(User.group_id == group.id, User.is_system_admin.is_(False)))
    db.execute(delete(Group).where(Group.id == group.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/casse/{cassa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cassa(cassa_id: uuid.UUID, db: DbSession, _: SystemAdmin) -> Response:
    cassa = get_cassa_or_404(db, cassa_id)
    delete_cassa_receipt_objects(db, cassa.id)
    db.execute(delete(Cassa).where(Cassa.id == cassa.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
