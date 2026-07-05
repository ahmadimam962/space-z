"""
Certificates Module
هذا الموديول مسؤول عن شهادات إكمال الكورسات:
- إصدار شهادة تلقائياً عند إكمال الكورس 100%
- عرض شهادات الطالب
- التحقق العام من شهادة عبر certificate_code
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, Course, User, Notification
from app.users import get_current_user


router = APIRouter(tags=["Certificates"])


def certificate_to_dict(certificate: Certificate, db: Session) -> dict:
    """تحويل شهادة إلى قاموس مناسب للـ frontend."""
    user = db.query(User).filter(User.id == certificate.user_id).first()
    course = db.query(Course).filter(Course.id == certificate.course_id).first()

    return {
        "id": certificate.id,
        "certificateCode": certificate.certificate_code,
        "issuedAt": certificate.issued_at,
        "student": {
            "id": user.id if user else None,
            "name": f"{user.first_name} {user.last_name}" if user else "-",
            "email": user.email if user else "-"
        },
        "course": {
            "id": course.id if course else None,
            "title": course.title if course else "-"
        }
    }


def generate_certificate_code() -> str:
    """توليد كود شهادة واضح وفريد."""
    return f"SZ-{uuid4().hex[:12].upper()}"


def create_certificate_if_eligible(db: Session, user_id: int, course_id: int) -> Optional[Certificate]:
    """
    إنشاء شهادة إذا لم تكن موجودة مسبقاً.
    الدالة لا تتحقق من نسبة التقدم؛ يتم استدعاؤها فقط بعد التأكد من 100%.
    """
    existing = db.query(Certificate).filter(
        Certificate.user_id == user_id,
        Certificate.course_id == course_id
    ).first()

    if existing:
        return None

    code = generate_certificate_code()
    while db.query(Certificate).filter(Certificate.certificate_code == code).first():
        code = generate_certificate_code()

    certificate = Certificate(
        user_id=user_id,
        course_id=course_id,
        certificate_code=code,
        issued_at=datetime.utcnow()
    )

    db.add(certificate)

    course = db.query(Course).filter(Course.id == course_id).first()
    db.add(Notification(
        user_id=user_id,
        title="تم إصدار شهادة جديدة",
        message=f"مبروك! تم إصدار شهادة إكمال كورس {course.title if course else ''}."
    ))

    return certificate


@router.get("/api/my-certificates")
def my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """عرض شهادات الطالب الحالي."""
    certificates = db.query(Certificate).filter(
        Certificate.user_id == current_user.id
    ).order_by(Certificate.issued_at.desc()).all()

    return {
        "success": True,
        "data": [certificate_to_dict(certificate, db) for certificate in certificates]
    }


@router.get("/api/certificates/{certificate_code}")
def verify_certificate(
    certificate_code: str,
    db: Session = Depends(get_db)
):
    """التحقق العام من صحة شهادة عبر كود الشهادة."""
    certificate = db.query(Certificate).filter(
        Certificate.certificate_code == certificate_code
    ).first()

    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    return {
        "success": True,
        "valid": True,
        "data": certificate_to_dict(certificate, db)
    }
