from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import DbSession, OperatorMembership
from app.models import AuditLog
from app.schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    db: DbSession,
    operator: OperatorMembership,
    limit: Annotated[int, Query(ge=1, le=200)] = 80,
) -> list[AuditLogRead]:
    rows = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .where(AuditLog.cassa_id == operator.cassa_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return [
        AuditLogRead(
            id=row.id,
            cassa_id=row.cassa_id,
            user_id=row.user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            summary=row.summary,
            details=row.details,
            created_at=row.created_at,
            user_name=row.user.name if row.user else None,
        )
        for row in rows
    ]
