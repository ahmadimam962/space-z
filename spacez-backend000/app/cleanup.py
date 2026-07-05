"""
Auth Data Cleanup Module
هذا الموديول مسؤول عن التنظيف الدوري لبيانات المصادقة المنتهية
لمنع تضخم قاعدة البيانات والحفاظ على الأمان.

المهام المستهدفة:
- حذف رموز OTP المنتهية الصلاحية
- حذف التسجيلات المعلقة القديمة (أقدم من 30 دقيقة)

يتم استدعاء هذا الموديول من قبل مهمة خلفية مجدولة (راجع main.py).
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import OTPCode, PendingRegistration


# ==========================================
# Cleanup Function
# ==========================================

def cleanup_expired_auth_data(db: Session) -> None:
    """
    حذف رموز OTP المنتهية والتسجيلات المعلقة القديمة من قاعدة البيانات.

    تقوم هذه الدالة بعمليتي تنظيف:
    1. حذف كل رموز OTP حيث expires_at < الوقت الحالي
    2. حذف كل التسجيلات المعلقة التي تم إنشاؤها منذ أكثر من 30 دقيقة

    Args:
        db (Session): جلسة قاعدة بيانات SQLAlchemy نشطة.

    Note:
        هذه الدالة تقوم بـ commit للـ transaction.
        على المستدعي إدارة دورة حياة الجلسة (فتح/إغلاق).
    """
    now = datetime.utcnow()

    # 1. حذف رموز OTP المنتهية
    db.query(OTPCode).filter(
        OTPCode.expires_at < now
    ).delete()

    # 2. حذف التسجيلات المعلقة الأقدم من 30 دقيقة
    # (مستخدمين لم يكملوا التحقق من البريد في الوقت المحدد)
    old_pending_time = now - timedelta(minutes=30)

    db.query(PendingRegistration).filter(
        PendingRegistration.created_at < old_pending_time
    ).delete()

    # Commit كلا العمليتين في transaction واحدة
    db.commit()