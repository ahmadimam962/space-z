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


# ==========================================
# Endpoints
# ==========================================

@router.get("")
def list_audit_logs(
    page: int = 1,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    offset = (page - 1) * limit

    query = db.query(AuditLog)

    total = query.count()

    logs = query.order_by(
        AuditLog.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "data": [audit_to_dict(log) for log in logs]
    }