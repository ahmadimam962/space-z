"""
Audit Logs Module
هذا الموديول مسؤول عن عرض سجلات العمليات الإدارية.
يتيح للإدارة مراجعة كافة الإجراءات التي تم تنفيذها في النظام
مثل: الموافقة على طلبات الشراء، حظر المستخدمين، منح الكورسات...
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(
    prefix="/api/admin/audit-logs",
    tags=["Audit Logs"]
)


# ==========================================
# Helper Functions
# ==========================================

def audit_to_dict(log: AuditLog) -> dict:
    """تحويل كائن AuditLog إلى قاموس للعرض."""
    return {
        "id": log.id,
        "adminId": log.admin_id,
        "action": log.action,
        "targetType": log.target_type,
        "targetId": log.target_id,
        "details": log.details,
        "createdAt": log.created_at
    }


# ==========================================
# Endpoints
# ==========================================

@router.get("")
def list_audit_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """سرد آخر 200 سجل تدقيق (الأحدث أولاً)."""
    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).limit(200).all()

    return {
        "success": True,
        "data": [audit_to_dict(log) for log in logs]
    }