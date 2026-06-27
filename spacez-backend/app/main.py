"""
FastAPI Application Entry Point
نقطة الدخول الرئيسية لتطبيق Space Z Backend.

المسؤوليات:
- تهيئة تطبيق FastAPI مع البيانات الوصفية
- إعداد Middleware (CORS)
- إنشاء جداول قاعدة البيانات عند بدء التشغيل
- تسجيل جميع الـ API Routers
- إعداد جدولة المهام الخلفية للتنظيف الدوري

المهام الخلفية:
- Auth cleanup: يعمل كل 60 دقيقة لحذف OTPs المنتهية والتسجيلات المعلقة
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import Base, engine, SessionLocal
from app.cleanup import cleanup_expired_auth_data

# استيراد جميع النماذج لتسجيلها في Base.metadata
from app.models import (
    User, OTPCode, PendingRegistration, UserDevice,
    Course, PaymentSetting, PurchaseRequest, Enrollment,
    Notification, CourseSection, CourseLesson,
    Coupon, AuditLog, LessonProgress
)

# استيراد جميع الـ Routers
from app.auth import router as auth_router
from app.users import router as users_router
from app.admin import router as admin_router
from app.courses import router as courses_router
from app.payments import router as payments_router
from app.purchases import router as purchases_router
from app.notifications import router as notifications_router
from app.enrollments import router as enrollments_router
from app.course_content import router as course_content_router
from app.audit import router as audit_router
from app.progress import router as progress_router


# ==========================================
# Database Initialization
# ==========================================
# إنشاء الجداول (في الإنتاج يُفضّل استخدام Alembic)
Base.metadata.create_all(bind=engine)


# ==========================================
# FastAPI Application Initialization
# ==========================================
app = FastAPI(
    title="Space Z API",
    version="1.0.0",
    description="Backend API for the Space Z e-learning platform"
)


# ==========================================
# Middleware Configuration
# ==========================================
# تحذير: allow_origins=["*"] للـ development فقط
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Background Scheduler Setup
# ==========================================
scheduler = BackgroundScheduler()


def scheduled_cleanup() -> None:
    """
    مهمة خلفية لتنظيف بيانات المصادقة المنتهية.
    تنشئ Session خاص بها لأنها تعمل خارج سياق الطلب.
    """
    db = SessionLocal()
    try:
        cleanup_expired_auth_data(db)
        print("Auth cleanup completed")
    finally:
        db.close()


@app.on_event("startup")
def start_scheduler() -> None:
    """بدء جدولة المهام عند تشغيل التطبيق."""
    scheduler.add_job(
        scheduled_cleanup,
        "interval",
        minutes=60,
        id="auth_cleanup",
        replace_existing=True
    )
    scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler() -> None:
    """إيقاف الجدولة عند إيقاف التطبيق."""
    scheduler.shutdown()


# ==========================================
# Router Registration
# ==========================================
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(courses_router)
app.include_router(payments_router)
app.include_router(purchases_router)
app.include_router(notifications_router)
app.include_router(enrollments_router)
app.include_router(course_content_router)
app.include_router(audit_router)
app.include_router(progress_router)


# ==========================================
# Root / Health Check Endpoint
# ==========================================
@app.get("/")
def root() -> dict:
    """نقطة فحص صحة الـ API."""
    return {
        "success": True,
        "message": "Space Z Backend Running"
    }