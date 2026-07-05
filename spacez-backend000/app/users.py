"""
User Management Router
هذا الموديول يعالج نقاط النهاية الخاصة بالمستخدمين:
- جلب الملف الشخصي
- إكمال/تحديث رقم الهاتف
- تغيير كلمة المرور
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

# Local imports
from app.database import get_db
from app.models import User
from app.security import decode_access_token, verify_password, hash_password
from app.schemas import CompletePhoneRequest, ChangePasswordRequest


# ==========================================
# Router & Security Initialization
# ==========================================
router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)
security = HTTPBearer()


# ==========================================
# Dependencies
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency لاستخراج والتحقق من المستخدم الحالي المصادق عليه.
    الخطوات:
    1. استخراج Bearer token من headers
    2. فك التوكن واستخراج payload
    3. جلب المستخدم من قاعدة البيانات
    4. التحقق من وجوده وعدم حظره
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account is banned")

    return user


# ==========================================
# Endpoints
# ==========================================

@router.get("/profile")
def profile(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """جلب معلومات الملف الشخصي للمستخدم المصادق عليه."""
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "email": current_user.email,
            "phoneNumber": current_user.phone_number,
            "role": current_user.role
        }
    }


@router.post("/complete-phone")
def complete_phone(
    request: CompletePhoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """تحديث أو إكمال رقم هاتف المستخدم المصادق عليه."""
    # التحقق من عدم استخدام الرقم من قبل مستخدم آخر
    existing_phone = db.query(User).filter(
        User.phone_number == request.phone_number,
        User.id != current_user.id
    ).first()

    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone already exists")

    current_user.phone_number = request.phone_number
    db.commit()

    return {
        "success": True,
        "message": "Phone number updated successfully",
        "data": {
            "id": current_user.id,
            "phoneNumber": current_user.phone_number
        }
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """تغيير كلمة مرور المستخدم (للمستخدمين المحليين فقط)."""
    # منع مستخدمي Google من تغيير كلمة المرور
    if current_user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="Google accounts cannot change password"
        )

    # التحقق من صحة كلمة المرور الحالية
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    # تحديث كلمة المرور
    current_user.password_hash = hash_password(request.new_password)
    db.commit()

    return {
        "success": True,
        "message": "Password changed successfully"
    }