from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.admin import get_current_admin


router = APIRouter(
    prefix="/api/admin/audit-logs",
    tags=["Audit Logs"]
)


def audit_to_dict(log: AuditLog):
    return {
        "id": log.id,
        "adminId": log.admin_id,
        "action": log.action,
        "targetType": log.target_type,
        "targetId": log.target_id,
        "details": log.details,
        "createdAt": log.created_at
    }


@router.get("")
def list_audit_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).limit(200).all()

    return {
        "success": True,
        "data": [
            audit_to_dict(log)
            for log in logs
        ]
    }