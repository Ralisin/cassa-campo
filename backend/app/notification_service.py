from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Movement, Notification, User, UserRole


def format_amount(amount: Decimal) -> str:
    return f"{amount:.2f}".replace(".", ",")


def notify_admins_of_movement(
    db: Session,
    movement: Movement,
    creator: User,
    *,
    reimbursement_requested: bool,
) -> None:
    recipients = list(
        db.scalars(select(User).where(User.role == UserRole.ADMIN, User.id != creator.id)).all()
    )
    if reimbursement_requested:
        recipients.extend(
            db.scalars(
                select(User).where(
                    User.role == UserRole.CASHIER,
                    User.branch == movement.unit,
                    User.id != creator.id,
                )
            ).all()
        )
    kind = "reimbursement_requested" if reimbursement_requested else "movement_created"
    title = "Nuovo rimborso da effettuare" if reimbursement_requested else "Nuovo movimento"
    message = (
        f"{creator.name} ha richiesto un rimborso di € {format_amount(movement.amount)} "
        f"per {movement.supplier}."
        if reimbursement_requested
        else f"{creator.name} ha aggiunto {movement.supplier} per € {format_amount(movement.amount)}."
    )
    db.add_all(
        [
            Notification(
                user_id=admin.id,
                movement_id=movement.id,
                kind=kind,
                title=title,
                message=message,
            )
            for admin in recipients
        ]
    )


def notify_reimbursement_completed(db: Session, movement: Movement) -> None:
    db.add(
        Notification(
            user_id=movement.created_by,
            movement_id=movement.id,
            kind="reimbursement_completed",
            title="Rimborso effettuato",
            message=(
                f"Il rimborso di € {format_amount(movement.amount)} "
                f"per {movement.supplier} è stato effettuato."
            ),
        )
    )
