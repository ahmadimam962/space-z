"""
Purchases Module
هذا الموديول مسؤول عن إدارة عمليات الشراء، بما في ذلك:
- إنشاء طلبات شراء للكورسات المدفوعة
- التسجيل التلقائي في الكورسات المجانية
- إدارة طلبات الشراء من قبل الإدارة (عرض، قبول، رفض)
- التنبيهات المتعلقة بحالة الطلبات
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local imports
from app.database import get_db
from app.models import (
    PurchaseRequest, Course, User, Enrollment, Notification, AuditLog
)
from app.schemas import PurchaseCourseRequest, PurchaseAdminNoteRequest
from app.users import get_current_user
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(tags=["Purchases"])


# ==========================================
# Helper Functions
# ==========================================

def purchase_to_admin_dict(purchase: PurchaseRequest, db: Session) -> Dict[str, Any]:
    """تحويل كائن PurchaseRequest إلى قاموس لعرض بياناته في لوحة تحكم الإدارة."""
    user = db.query(User).filter(User.id == purchase.user_id).first()
    course = db.query(Course).filter(Course.id == purchase.course_id).first()

    return {
        "id": purchase.id,
        "status": purchase.status,
        "transferNumber": purchase.transfer_number,
        "adminNote": purchase.admin_note,
        "createdAt": purchase.created_at,
        "student": {
            "id": user.id if user else None,
            "name": f"{user.first_name} {user.last_name}" if user else "-",
            "email": user.email if user else "-",
            "phoneNumber": user.phone_number if user else "-"
        },
        "course": {
            "id": course.id if course else None,
            "title": course.title if course else "-",
            "price": course.price if course else 0
        }
    }


# ==========================================
# User Endpoints
# ==========================================

@router.post("/api/purchases")
def create_purchase_request(
    request: PurchaseCourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """إنشاء طلب شراء جديد لكورس معين."""
    # 1. التحقق من وجود الكورس وحالته
    course = db.query(Course).filter(
        Course.id == request.course_id,
        Course.status == "active"
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. التحقق مما إذا كان المستخدم يمتلك الكورس بالفعل
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course.id,
        Enrollment.status == "active"
    ).first()
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="You already own this course")

    # 3. معالجة الكورسات المجانية (تسجيل فوري)
    if not course.is_paid or course.price == 0:
        db.add(Enrollment(
            user_id=current_user.id,
            course_id=course.id,
            status="active"
        ))
        db.add(Notification(
            user_id=current_user.id,
            title="تم تفعيل الكورس المجاني",
            message=f"تمت إضافة كورس {course.title} إلى حسابك."
        ))
        db.commit()
        return {
            "success": True,
            "message": "Free course enrolled successfully",
            "freeCourse": True
        }

    # 4. التحقق من وجود طلب معلق أو رقم تحويلة مكرر
    pending_request = db.query(PurchaseRequest).filter(
        PurchaseRequest.user_id == current_user.id,
        PurchaseRequest.course_id == course.id,
        PurchaseRequest.status == "pending"
    ).first()
    if pending_request:
        raise HTTPException(status_code=400, detail="You already have a pending request")

    duplicate_transfer = db.query(PurchaseRequest).filter(
        PurchaseRequest.transfer_number == request.transfer_number,
        PurchaseRequest.status.in_(["pending", "approved"])
    ).first()
    if duplicate_transfer:
        raise HTTPException(status_code=400, detail="Transfer number already used")

    # 5. إنشاء الطلب
    db.add(PurchaseRequest(
        user_id=current_user.id,
        course_id=course.id,
        transfer_number=request.transfer_number,
        status="pending"
    ))
    db.commit()

    return {"success": True, "message": "Purchase request submitted successfully"}


@router.get("/api/my-purchases")
def my_purchase_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """استرجاع سجل مشتريات المستخدم الحالي."""
    purchases = db.query(PurchaseRequest)\
        .filter(PurchaseRequest.user_id == current_user.id)\
        .order_by(PurchaseRequest.created_at.desc())\
        .all()

    result = []
    for p in purchases:
        course = db.query(Course).filter(Course.id == p.course_id).first()
        result.append({
            "id": p.id,
            "status": p.status,
            "transferNumber": p.transfer_number,
            "adminNote": p.admin_note,
            "createdAt": p.created_at,
            "course": {
                "id": course.id if course else None,
                "title": course.title if course else "-",
                "price": course.price if course else 0
            }
        })

    return {"success": True, "data": result}


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/purchase-requests")
def admin_list_purchase_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """سرد طلبات الشراء لمراجعتها من قبل الإدارة."""
    query = db.query(PurchaseRequest)
    if status:
        query = query.filter(PurchaseRequest.status == status)

    purchases = query.order_by(PurchaseRequest.created_at.desc()).all()
    return {
        "success": True,
        "data": [purchase_to_admin_dict(p, db) for p in purchases]
    }


@router.post("/api/admin/purchase-requests/{purchase_id}/approve")
def approve_purchase_request(
    purchase_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """الموافقة على طلب شراء."""
    purchase = db.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_id).first()
    if not purchase or purchase.status != "pending":
        raise HTTPException(status_code=400, detail="Purchase request invalid or not pending")

    # تحديث حالة الطلب
    purchase.status = "approved"

    # إنشاء التسجيل في الكورس إن لم يكن موجوداً
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == purchase.user_id,
        Enrollment.course_id == purchase.course_id
    ).first()
    if not existing_enrollment:
        db.add(Enrollment(
            user_id=purchase.user_id,
            course_id=purchase.course_id,
            status="active"
        ))

    # إشعار المستخدم + سجل التدقيق
    db.add(Notification(
        user_id=purchase.user_id,
        title="تم قبول طلب الشراء",
        message="تم قبول طلبك وتفعيل الكورس."
    ))
    db.add(AuditLog(
        admin_id=admin.id,
        action="approve_purchase",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Approved purchase {purchase.id}"
    ))
    db.commit()

    return {"success": True, "message": "Purchase request approved successfully"}


@router.post("/api/admin/purchase-requests/{purchase_id}/reject")
def reject_purchase_request(
    purchase_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """رفض طلب شراء."""
    purchase = db.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_id).first()
    if not purchase or purchase.status != "pending":
        raise HTTPException(status_code=400, detail="Purchase request invalid or not pending")

    purchase.status = "rejected"

    db.add(Notification(
        user_id=purchase.user_id,
        title="تم رفض طلب الشراء",
        message="تم رفض طلبك. يرجى التواصل مع الدعم."
    ))
    db.add(AuditLog(
        admin_id=admin.id,
        action="reject_purchase",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Rejected purchase {purchase.id}"
    ))
    db.commit()

    return {"success": True, "message": "Purchase request rejected successfully"}


@router.put("/api/admin/purchase-requests/{purchase_id}/note")
def update_purchase_admin_note(
    purchase_id: int,
    request: PurchaseAdminNoteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """إضافة/تحديث ملاحظة إدارية على طلب الشراء."""
    purchase = db.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    purchase.admin_note = request.admin_note

    db.add(AuditLog(
        admin_id=admin.id,
        action="update_purchase_note",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Updated note for {purchase.id}"
    ))
    db.commit()

    return {"success": True, "message": "Admin note updated successfully"}


@router.get("/api/admin/users/{user_id}/purchases")
def admin_user_purchase_history(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """استرجاع سجل مشتريات مستخدم محدد (للإدارة)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    purchases = db.query(PurchaseRequest)\
        .filter(PurchaseRequest.user_id == user_id)\
        .order_by(PurchaseRequest.created_at.desc())\
        .all()

    return {
        "success": True,
        "data": [purchase_to_admin_dict(p, db) for p in purchases]
    }