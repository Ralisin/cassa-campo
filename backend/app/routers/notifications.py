import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select, update

from app.dependencies import CurrentMembership, CurrentUser, DbSession
from app.models import Movement, Notification
from app.schemas import NotificationList, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(
    db: DbSession,
    membership: CurrentMembership,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> NotificationList:
    cassa_ids = (
        select(Movement.id).where(Movement.cassa_id == membership.cassa_id).scalar_subquery()
    )
    items = db.scalars(
        select(Notification)
        .where(
            Notification.user_id == membership.user_id,
            Notification.movement_id.in_(cassa_ids),
        )
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    ).all()
    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == membership.user_id,
            Notification.movement_id.in_(cassa_ids),
            Notification.read_at.is_(None),
        )
    ) or 0
    return NotificationList(items=list(items), unread_count=unread_count)


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(db: DbSession, membership: CurrentMembership) -> Response:
    cassa_ids = (
        select(Movement.id).where(Movement.cassa_id == membership.cassa_id).scalar_subquery()
    )
    db.execute(
        update(Notification)
        .where(
            Notification.user_id == membership.user_id,
            Notification.movement_id.in_(cassa_ids),
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
    return notification
