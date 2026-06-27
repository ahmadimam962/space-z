"""
Payment Settings Module
هذا الموديول مسؤول عن إدارة إعدادات طرق الدفع، بما في ذلك:
- عرض طرق الدفع النشطة للجمهور (بدون مصادقة)
- عمليات CRUD للإدارة (إنشاء، قراءة، تحديث، حذف)
إعدادات الدفع تمثل الطرق المتاحة للمستخدمين لشراء الكورسات
(مثل: تحويل بنكي، باي بال، إلخ).
"""
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local imports
from app.database import get_db
from app.models import PaymentSetting, User
from app.schemas import (
    PaymentSettingCreateRequest,
    PaymentSettingUpdateRequest
)
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(tags=["Payment Settings"])


# ==========================================
# Helper Functions
# ==========================================

def payment_to_dict(payment: PaymentSetting) -> Dict[str, Any]:
    """
    تحويل كائن PaymentSetting إلى قاموس لاستجابات الـ API.
    يقوم بتحويل أسماء الحقول من snake_case إلى camelCase لتوافق الواجهة الأمامية.
    """
    return {
        "id": payment.id,
        "methodName": payment.method_name,
        "accountName": payment.account_name,
        "accountNumber": payment.account_number,
        "instructions": payment.instructions,
        "isActive": payment.is_active,
        "createdAt": payment.created_at
    }


# ==========================================
# Public Endpoints (No Auth Required)
# ==========================================

@router.get("/api/payment-settings")
def list_public_payment_settings(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    عرض جميع إعدادات الدفع النشطة للاستخدام العام.
    هذا الـ endpoint متاح بدون مصادقة ويُرجع فقط طرق الدفع النشطة حالياً.
    """
    payments = db.query(PaymentSetting).filter(
        PaymentSetting.is_active.is_(True)
    ).order_by(
        PaymentSetting.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [payment_to_dict(p) for p in payments]
    }


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/payment-settings")
def admin_list_payment_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """سرد جميع إعدادات الدفع لمراجعتها من قبل الإدارة (تشمل غير النشطة)."""
    payments = db.query(PaymentSetting).order_by(
        PaymentSetting.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [payment_to_dict(p) for p in payments]
    }


@router.post("/api/admin/payment-settings")
def create_payment_setting(
    request: PaymentSettingCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """إنشاء إعداد دفع جديد."""
    payment = PaymentSetting(
        method_name=request.method_name,
        account_name=request.account_name,
        account_number=request.account_number,
        instructions=request.instructions,
        is_active=request.is_active
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "success": True,
        "message": "Payment setting created successfully",
        "data": payment_to_dict(payment)
    }


@router.put("/api/admin/payment-settings/{payment_id}")
def update_payment_setting(
    payment_id: int,
    request: PaymentSettingUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    تحديث إعداد دفع موجود (يدعم التحديث الجزئي).
    يتم تحديث الحقول غير None فقط.
    """
    payment = db.query(PaymentSetting).filter(
        PaymentSetting.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment setting not found"
        )

    # تحديث الحقول المقدمة فقط
    if request.method_name is not None:
        payment.method_name = request.method_name

    if request.account_name is not None:
        payment.account_name = request.account_name

    if request.account_number is not None:
        payment.account_number = request.account_number

    if request.instructions is not None:
        payment.instructions = request.instructions

    if request.is_active is not None:
        payment.is_active = request.is_active

    db.commit()
    db.refresh(payment)

    return {
        "success": True,
        "message": "Payment setting updated successfully",
        "data": payment_to_dict(payment)
    }


@router.delete("/api/admin/payment-settings/{payment_id}")
def delete_payment_setting(
    payment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """حذف إعداد دفع بشكل نهائي."""
    payment = db.query(PaymentSetting).filter(
        PaymentSetting.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment setting not found"
        )

    db.delete(payment)
    db.commit()

    return {
        "success": True,
        "message": "Payment setting deleted successfully"
    }