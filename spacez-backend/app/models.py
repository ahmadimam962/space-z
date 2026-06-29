"""
Database Models Module
هذا الموديول يعرّف كافة نماذج SQLAlchemy ORM لقاعدة البيانات.
كل نموذج يمثل جدول مع أعمدته وعلاقاته.

النماذج المتضمنة:
- User: حسابات المستخدمين (طلاب، أدمن)
- OTPCode: رموز التحقق لمرة واحدة
- PendingRegistration: تخزين التسجيلات غير المكتملة
- UserDevice: تتبع أجهزة المستخدمين
- Course: معلومات الكورسات
- PaymentSetting: إعدادات طرق الدفع
- PurchaseRequest: طلبات شراء الكورسات
- Enrollment: تسجيلات المستخدمين في الكورسات
- Notification: إشعارات المستخدمين
- CourseSection: أقسام الكورسات
- CourseLesson: دروس الكورسات
- Coupon: كوبونات الخصم
- AuditLog: سجل العمليات الإدارية
- LessonProgress: تتبع تقدم الدروس
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Index
)
from app.database import Base


# ==========================================
# User Management Models
# ==========================================

class User(Base):
    """حساب المستخدم الرئيسي (طالب أو أدمن)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(30), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="student")
    auth_provider = Column(String(20), default="local")
    is_email_verified = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class OTPCode(Base):
    """رموز OTP للتحقق من البريد وإعادة تعيين كلمة المرور."""
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    code = Column(String(255), nullable=False)
    purpose = Column(String(50), default="register")
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PendingRegistration(Base):
    """تخزين مؤقت للتسجيلات غير المكتملة قبل التحقق من OTP."""
    __tablename__ = "pending_registrations"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserDevice(Base):
    """تتبع الأجهزة لتسجيلات دخول المستخدم."""
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "uq_user_device_user_device",
            "user_id",
            "device_id",
            unique=True
        ),
    )


# ==========================================
# Course Management Models
# ==========================================

class Course(Base):
    """معلومات الكورس وبياناته الوصفية."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False, default=0)
    thumbnail_url = Column(String(500), nullable=True)
    status = Column(String(20), default="hidden")  # active / hidden / coming_soon
    is_paid = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# Payment & Purchase Models
# ==========================================

class PaymentSetting(Base):
    """إعدادات طرق الدفع اليدوية (تحويل بنكي، باي بال...)."""
    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)
    method_name = Column(String(100), nullable=False)
    account_name = Column(String(255), nullable=True)
    account_number = Column(String(255), nullable=False)
    instructions = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseRequest(Base):
    """طلب شراء كورس مدفوع مع رقم التحويلة للمراجعة."""
    __tablename__ = "purchase_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    transfer_number = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")  # pending / approved / rejected
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "uq_active_purchase_transfer_number",
            "transfer_number",
            unique=True,
            postgresql_where=status.in_(["pending", "approved"])
        ),
        Index(
            "uq_active_purchase_user_course",
            "user_id",
            "course_id",
            unique=True,
            postgresql_where=status.in_(["pending", "approved"])
        ),
    )


class Enrollment(Base):
    """تسجيل المستخدم في كورس (تلقائي للمجاني أو بعد الموافقة للمدفع)."""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="active")  # active / completed / cancelled
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "uq_active_enrollment_user_course",
            "user_id",
            "course_id",
            unique=True,
            postgresql_where=(status == "active")
        ),
    )


# ==========================================
# Notification Models
# ==========================================

class Notification(Base):
    """إشعارات المستخدمين للأحداث المهمة."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# Course Content Models
# ==========================================

class CourseSection(Base):
    """أقسام الكورس لتنظيم الدروس."""
    __tablename__ = "course_sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class CourseLesson(Base):
    """الدروس داخل أقسام الكورس (فيديو / PDF / نص)."""
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    lesson_type = Column(String(50), default="video")  # video / pdf / text
    video_provider = Column(String(50), nullable=True)  # local / bunny / drive / external
    video_url = Column(String(1000), nullable=True)
    pdf_url = Column(String(1000), nullable=True)
    content_text = Column(String, nullable=True)
    sort_order = Column(Integer, default=1)
    is_free_preview = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Coupon(Base):
    """كوبونات الخصم على الكورسات."""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False)
    discount_type = Column(String(20), default="percent")  # percent / fixed
    discount_value = Column(Integer, nullable=False)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """سجل العمليات الإدارية للمراجعة والتدقيق."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    action = Column(String(255), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LessonProgress(Base):
    """تتبع تقدم المستخدم في الدروس (مكتمل / قيد المشاهدة)."""
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    last_watched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "uq_lesson_progress_user_lesson",
            "user_id",
            "lesson_id",
            unique=True
        ),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "uq_refresh_token_user_device",
            "user_id",
            "device_id",
            unique=True
        ),
    )