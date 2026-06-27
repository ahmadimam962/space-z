"""
Notifications Module
هذا الموديول مسؤول عن إدارة إشعارات المستخدم:
- عرض قائمة الإشعارات مع عدد غير المقروءة
- تحديد إشعار كمقروء
- تحديد جميع الإشعارات كمقروءة
"""
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, User
from app.users import get_current_user


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"]
)


# ==========================================
# Helper Functions
# ==========================================

def notification_to_dict(notification: Notification) -> Dict[str, Any]:
    """تحويل كائن Notification إلى قاموس للعرض."""
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "isRead": notification.is_read,
        "createdAt": notification.created_at
    }


# ==========================================
# Endpoints
# ==========================================

@router.get("")
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """سرد إشعارات المستخدم الحالي مع عدد غير المقروءة."""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    return {
        "success": True,
        "unreadCount": unread_count,
        "data": [notification_to_dict(n) for n in notifications]
    }


@router.post("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديد إشعار معين كمقروء."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()

    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.post("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديد جميع إشعارات المستخدم كمقروءة."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({Notification.is_read: True})

    db.commit()

    return {
        "success": True,
        "message": "All notifications marked as read"
    }