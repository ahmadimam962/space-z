"""
FastAPI Application Entry Point
---------------------------------
This is the main entry point for the Space Z backend application.

Responsibilities:
1. Initialize the FastAPI application with metadata
2. Configure middleware (CORS)
3. Create database tables on startup
4. Register all API routers
5. Set up background scheduler for periodic cleanup tasks
6. Provide a root health-check endpoint

Background Jobs:
- Auth cleanup: Runs every 60 minutes to remove expired OTPs and stale registrations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import Base, engine, SessionLocal
from app.cleanup import cleanup_expired_auth_data

# Import all models to ensure they're registered with Base.metadata
# (required for create_all to work properly)
from app.models import (
    User,
    OTPCode,
    PendingRegistration,
    UserDevice,
    Course,
    PaymentSetting,
    PurchaseRequest,
    Enrollment,
    Notification,
    CourseSection,
    CourseLesson,
    Coupon,
    AuditLog
)

# Import all API routers
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
# FastAPI Application Initialization
# ==========================================

# Create all database tables (if they don't already exist)
# Note: In production, prefer using Alembic migrations instead

# Initialize the FastAPI application
app = FastAPI(
    title="Space Z API",
    version="1.0.0",
    description="Backend API for the Space Z e-learning platform"
)


# ==========================================
# Middleware Configuration
# ==========================================

# Configure CORS (Cross-Origin Resource Sharing) middleware
# WARNING: allow_origins=["*"] is for development only!
# In production, restrict to specific frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Background Scheduler Setup
# ==========================================

# Initialize APScheduler for running periodic background tasks
scheduler = BackgroundScheduler()


def scheduled_cleanup() -> None:
    """
    Background job that cleans up expired authentication data.
    
    Creates its own database session (since it runs outside of request context),
    performs the cleanup, and ensures the session is closed afterwards.
    """
    db = SessionLocal()
    try:
        cleanup_expired_auth_data(db)
        print("Auth cleanup completed")
    finally:
        db.close()


@app.on_event("startup")
def start_scheduler() -> None:
    """
    Start the background scheduler when the application starts.
    
    Registers the auth cleanup job to run every 60 minutes.
    replace_existing=True prevents duplicate jobs if the app restarts.
    """
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
    """
    Gracefully shut down the background scheduler when the application stops.
    """
    scheduler.shutdown()


# ==========================================
# Router Registration
# ==========================================

# Register all API routers with the FastAPI app
# Each router handles a specific domain (auth, users, courses, etc.)
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
    """
    Root endpoint - serves as a health check for the API.
    
    Returns:
        dict: A simple success response confirming the API is running.
    """
    return {
        "success": True,
        "message": "Space Z Backend Running"
    }