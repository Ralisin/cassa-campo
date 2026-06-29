import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    summary: str,
    cassa_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            cassa_id=cassa_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:255],
            details=json.dumps(details, default=str, ensure_ascii=False) if details else None,
        )
    )
