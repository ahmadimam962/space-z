"""
Admin Module
هذا الموديول يعالج كافة العمليات الإدارية بما في ذلك:

مصادقة الأدمن:
- dependency للتحقق من صلاحيات الأدمن (role-based access control)

نقاط نهاية لوحة التحكم:
- إحصائيات النظام (المستخدمين، الطلاب، الأدمن، المحظورين، مزودي المصادقة)

نقاط نهاية إدارة المستخدمين:
- سرد المستخدمين (مع البحث، الفلاتر، pagination)
- جلب تفاصيل المستخدم (مع سجل الأجهزة)
- حظر/إلغاء حظر المستخدمين
- حذف المستخدمين (مع تنظيف الأجهزة)
- إزالة أجهزة المستخدم

جميع نقاط النهاية الإدارية تتطلب مصادقة بدور "admin".
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Local imports
from app.database import get_db
from app.models import User, UserDevice
from app.users import get_current_user
from app.audit_utils import create_audit_log
# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


# ==========================================
# Dependencies
# ==========================================

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency للتحقق من أن المستخدم الحالي لديه صلاحيات أدمن.
    يعتمد على get_current_user لـ:
    1. التحقق من JWT token
    2. جلب المستخدم من قاعدة البيانات
    3. التحقق من أن دور المستخدم هو "admin"
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


# ==========================================
# Dashboard Endpoints
# ==========================================

@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    جلب إحصائيات النظام للوحة تحكم الأدمن.
    تُرجع عدد: المستخدمين الكلي، الطلاب، الأدمن، المحظورين،
    مستخدمي Google OAuth، والمستخدمين المحليين.
    """
    total_users = db.query(User).count()

    total_students = db.query(User).filter(
        User.role == "student"
    ).count()

    total_admins = db.query(User).filter(
        User.role == "admin"
    ).count()

    banned_users = db.query(User).filter(
        User.is_banned.is_(True)
    ).count()

    google_users = db.query(User).filter(
        User.auth_provider == "google"
    ).count()

    local_users = db.query(User).filter(
        User.auth_provider == "local"
    ).count()

    return {
        "success": True,
        "data": {
            "totalUsers": total_users,
            "totalStudents": total_students,
            "totalAdmins": total_admins,
            "bannedUsers": banned_users,
            "googleUsers": google_users,
            "localUsers": local_users
        }
    }


# ==========================================
# User Management Endpoints
# ==========================================

@router.get("/users")
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_banned: Optional[bool] = None,
    auth_provider: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    سرد المستخدمين مع البحث، الفلاتر، والـ pagination.
    يدعم:
    - البحث بالاسم، البريد، أو رقم الهاتف (case-insensitive partial match)
    - الفلترة حسب الدور (student/admin)
    - الفلترة حسب حالة الحظر
    - الفلترة حسب مزود المصادقة (local/google)
    - Pagination بـ limit و offset
    """
    # 1. بناء الاستعلام الأساسي
    query = db.query(User)

    # 2. تطبيق فلتر البحث (case-insensitive partial match)
    if search:
        query = query.filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone_number.ilike(f"%{search}%")
            )
        )

    # 3. تطبيق فلتر الدور
    if role:
        query = query.filter(User.role == role)

    # 4. تطبيق فلتر حالة الحظر
    if is_banned is not None:
        query = query.filter(User.is_banned == is_banned)

    # 5. تطبيق فلتر مزود المصادقة
    if auth_provider:
        query = query.filter(User.auth_provider == auth_provider)

    # 6. الحصول على العدد الإجمالي (قبل pagination)
    total = query.count()

    # 7. تطبيق pagination والترتيب (الأحدث أولاً)
    users = query.order_by(
        User.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "data": [
            {
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "phoneNumber": user.phone_number,
                "role": user.role,
                "authProvider": user.auth_provider,
                "isEmailVerified": user.is_email_verified,
                "isBanned": user.is_banned,
                "createdAt": user.created_at
            }
            for user in users
        ]
    }


@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """جلب معلومات تفصيلية عن مستخدم محدد، بما في ذلك سجل الأجهزة."""
    # 1. جلب المستخدم
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. جلب جميع الأجهزة لهذا المستخدم
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == user.id
    ).all()

    return {
        "success": True,
        "data": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "phoneNumber": user.phone_number,
            "role": user.role,
            "authProvider": user.auth_provider,
            "isEmailVerified": user.is_email_verified,
            "isBanned": user.is_banned,
            "createdAt": user.created_at,
            "devices": [
                {
                    "id": device.id,
                    "deviceId": device.device_id,
                    "createdAt": device.created_at,
                    "lastLoginAt": device.last_login_at
                }
                for device in devices
            ]
        }
    }


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """حظر حساب مستخدم، مما يمنعه من تسجيل الدخول."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # منع الأدمن من حظر نفسه
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot ban yourself"
        )
    
    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="ban_user",
        target_type="user",
        target_id=user.id,
        details=f"Banned user {user.id} - {user.email}"
    )
    user.is_banned = True
    db.commit()

    return {
        "success": True,
        "message": "User banned successfully"
    }


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """إلغاء حظر حساب مستخدم، واستعادة وصوله."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="unban_user",
        target_type="user",
        target_id=user.id,
        details=f"Unbanned user {user.id} - {user.email}"
    )

    user.is_banned = False
    db.commit()

    return {
        "success": True,
        "message": "User unbanned successfully"
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    حذف حساب مستخدم بشكل نهائي مع جميع الأجهزة المرتبطة.
    تحذير: هذا حذف نهائي (hard delete).
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # منع الأدمن من حذف نفسه
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete yourself"
        )

    # حذف جميع الأجهزة المرتبطة أولاً
    db.query(UserDevice).filter(
        UserDevice.user_id == user.id
    ).delete()

    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="delete_user",
        target_type="user",
        target_id=user.id,
        details=f"Deleted user {user.id} - {user.email}"
    )

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "User deleted successfully"
    }


@router.delete("/users/{user_id}/devices/{device_id}")
def remove_user_device(
    user_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    إزالة جهاز محدد من حساب المستخدم.
    يجبر هذا المستخدم على إعادة المصادقة على ذلك الجهاز عند تسجيل الدخول القادم.
    """
    device = db.query(UserDevice).filter(
        UserDevice.id == device_id,
        UserDevice.user_id == user_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="remove_user_device",
        target_type="user_device",
        target_id=device.id,
        details=f"Removed device {device.device_id} from user {user_id}"
    )

    db.delete(device)
    db.commit()

    return {
        "success": True,
        "message": "Device removed successfully"
    }