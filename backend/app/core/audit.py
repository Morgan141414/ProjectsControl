from sqlalchemy.orm import Session

from app.models.activity import AuditLog
from app.models.enums import AuditAction


def log_audit(
    db: Session,
    org_id: str,
    actor_id: str,
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    details: str | None = None,
) -> None:
    db.add(
        AuditLog(
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
