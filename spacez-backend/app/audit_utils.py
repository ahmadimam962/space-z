from sqlalchemy.orm import Session
from app.models import AuditLog


def create_audit_log(
    db: Session,
    admin_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    details: str | None = None
):
    audit = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )

    db.add(audit)
    return audit