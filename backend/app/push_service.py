import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Notification, PushSubscription


def push_enabled() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def push_payload(notification: Notification) -> dict[str, Any]:
    target = (
        "/rimborsi"
        if notification.kind == "reimbursement_completed"
        else f"/movimenti/{notification.movement_id}"
    )
    return {
        "title": notification.title,
        "body": notification.message,
        "url": target,
        "tag": str(notification.id),
        "data": {
            "notification_id": str(notification.id),
            "movement_id": str(notification.movement_id),
            "kind": notification.kind,
            "url": target,
        },
    }


def send_push_for_notification(db: Session, notification: Notification) -> None:
    if not push_enabled():
        return

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return

    subscriptions = list(
        db.scalars(
            select(PushSubscription).where(PushSubscription.user_id == notification.user_id)
        ).all()
    )
    if not subscriptions:
        return

    payload = json.dumps(push_payload(notification), separators=(",", ":"))
    stale_subscriptions: list[PushSubscription] = []
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": f"mailto:{settings.vapid_claim_email}"},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                stale_subscriptions.append(subscription)
        except Exception:
            # Push delivery is best-effort and must not block accounting actions.
            continue

    for subscription in stale_subscriptions:
        db.delete(subscription)


def send_push_for_notifications(db: Session, notifications: list[Notification]) -> None:
    for notification in notifications:
        send_push_for_notification(db, notification)
