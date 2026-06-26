"""
Database Models Module
----------------------
This module defines all SQLAlchemy ORM models for the application database.
Each model represents a table in the database with its columns and relationships.

Models included:
1. User - Main user accounts (students, admins)
2. OTPCode - One-time password codes for verification
3. PendingRegistration - Temporary storage for incomplete registrations
4. UserDevice - Device tracking for user sessions
5. Course - Course information and metadata
6. PaymentSetting - Payment method configurations
7. PurchaseRequest - Course purchase requests and their status
8. Enrollment - User enrollments in courses
9. Notification - User notifications

All models inherit from Base (defined in app.database)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime,ForeignKey, Index
from app.database import Base


# ==========================================
# User Management Models
# ==========================================

class User(Base):
    """
    Main user account model.
    
    Stores both student and admin accounts. Authentication can be local
    (email/password) or via OAuth providers (Google).
    
    Attributes:
        id: Unique user identifier (primary key).
        first_name: User's first name.
        last_name: User's last name.
        email: Unique email address for authentication.
        phone_number: Optional unique phone number for additional verification.
        password_hash: Hashed password (nullable for OAuth users).
        role: User role ("student" or "admin").
        auth_provider: Authentication method ("local", "google", etc.).
        is_email_verified: Whether the email has been verified via OTP.
        is_banned: Whether the account is banned from accessing the system.
        created_at: Timestamp when the account was created.
    """
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
    """
    One-Time Password (OTP) codes for email verification and password reset.
    
    OTPs are single-use codes sent to users' email addresses for:
    - Email verification during registration
    - Password reset requests
    
    Attributes:
        id: Unique OTP record identifier.
        email: Email address the OTP was sent to.
        code: Hashed OTP code (never store plain text).
        purpose: Purpose of the OTP ("register", "reset_password", etc.).
        is_used: Whether this OTP has been used (prevents replay attacks).
        expires_at: Timestamp when this OTP expires.
        created_at: Timestamp when this OTP was created.
    """
    __tablename__ = "otp_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    email = Column(String(255), nullable=False)
    
    code = Column(String(255), nullable=False)
    
    purpose = Column(String(50), default="register")
    
    is_used = Column(Boolean, default=False)
    
    expires_at = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PendingRegistration(Base):
    """
    Temporary storage for incomplete user registrations.
    
    When a user starts registration but hasn't verified their email yet,
    their data is stored here until OTP verification is complete.
    
    Attributes:
        id: Unique pending registration identifier.
        first_name: User's first name.
        last_name: User's last name.
        email: Unique email address (reserved until registration completes).
        phone_number: Unique phone number (reserved until registration completes).
        password_hash: Hashed password (stored securely until activation).
        created_at: Timestamp when this pending registration was created.
    """
    __tablename__ = "pending_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(30), unique=True, nullable=False)
    
    password_hash = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserDevice(Base):
    """
    Device tracking for user sessions and security.
    
    Tracks which devices a user has logged in from for:
    - Session management
    - Security monitoring
    - Multi-device support
    
    Attributes:
        id: Unique device record identifier.
        user_id: ID of the user who owns this device.
        device_id: Unique identifier for the device (from client).
        created_at: Timestamp when this device was first registered.
        last_login_at: Timestamp of the most recent login from this device.
    """
    __tablename__ = "user_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)


# ==========================================
# Course Management Models
# ==========================================

class Course(Base):
    """
    Course information and metadata.
    
    Represents a course that users can enroll in. Courses can be:
    - Free (is_paid=False or price=0) - auto-enrollment
    - Paid (is_paid=True and price>0) - requires purchase request
    
    Attributes:
        id: Unique course identifier.
        title: Course title (displayed to users).
        description: Optional detailed course description.
        price: Course price in smallest currency unit (e.g., cents). 0 for free courses.
        thumbnail_url: Optional URL for course thumbnail image.
        status: Course visibility status ("active", "hidden", "draft").
        is_paid: Whether this course requires payment to access.
        created_at: Timestamp when this course was created.
    """
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False, default=0)
    thumbnail_url = Column(String(500), nullable=True)
    
    status = Column(String(20), default="hidden")  # active / hidden / coming_soon
    is_paid = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    is_featured = Column(Boolean, default=False)


# ==========================================
# Payment & Purchase Models
# ==========================================

class PaymentSetting(Base):
    """
    Payment method configuration for manual payment processing.
    
    Stores details for bank transfers, PayPal accounts, or other
    manual payment methods that users can use to purchase courses.
    
    Attributes:
        id: Unique payment setting identifier.
        method_name: Name of the payment method (e.g., "Bank Transfer", "PayPal").
        account_name: Optional name of the account holder.
        account_number: Account number or identifier for the payment method.
        instructions: Optional instructions for customers on how to complete payment.
        is_active: Whether this payment method is currently available for use.
        created_at: Timestamp when this payment setting was created.
    """
    __tablename__ = "payment_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    method_name = Column(String(100), nullable=False)
    account_name = Column(String(255), nullable=True)
    account_number = Column(String(255), nullable=False)
    instructions = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseRequest(Base):
    """
    Course purchase request and payment verification.
    
    When a user wants to purchase a paid course, they submit a purchase request
    with their payment transfer number. Admins then verify the payment and
    approve/reject the request.
    
    Status flow:
    - pending: Initial state after user submits request
    - approved: Payment verified, user enrolled in course
    - rejected: Payment verification failed
    
    Attributes:
        id: Unique purchase request identifier.
        user_id: ID of the user making the purchase.
        course_id: ID of the course being purchased.
        transfer_number: Payment transaction reference number from the user.
        status: Current status of the purchase request.
        admin_note: Optional note from admin (e.g., rejection reason).
        created_at: Timestamp when this purchase request was created.
    """
    __tablename__ = "purchase_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    
    transfer_number = Column(String(255), nullable=False)
    
    status = Column(String(20), default="pending")  # pending / approved / rejected
    admin_note = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

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
    """
    User enrollment in a course.
    
    Tracks which courses a user has access to. Created either:
    - Automatically for free courses upon purchase request
    - Manually by admin after approving a paid course purchase
    
    Attributes:
        id: Unique enrollment identifier.
        user_id: ID of the enrolled user.
        course_id: ID of the enrolled course.
        status: Enrollment status ("active", "completed", "cancelled").
        enrolled_at: Timestamp when the user enrolled in the course.
    """
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    
    status = Column(String(20), default="active")
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

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
    """
    User notifications for important events and updates.
    
    Notifications are sent to users for events like:
    - Course enrollment confirmation
    - Purchase request approval/rejection
    - System announcements
    
    Attributes:
        id: Unique notification identifier.
        user_id: ID of the user who will receive this notification.
        title: Notification title (short summary).
        message: Detailed notification message.
        is_read: Whether the user has read this notification.
        created_at: Timestamp when this notification was created.
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    message = Column(String, nullable=False)
    
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

class CourseSection(Base):
    __tablename__ = "course_sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False, index=True)

    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)


class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    section_id = Column(Integer, nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)

    lesson_type = Column(String(50), default="video")  # video / pdf / text
    video_provider = Column(String(50), nullable=True) # local / bunny / drive / external
    video_url = Column(String(1000), nullable=True)
    pdf_url = Column(String(1000), nullable=True)
    content_text = Column(String, nullable=True)

    sort_order = Column(Integer, default=1)
    is_free_preview = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False, index=True)


class Coupon(Base):
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
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    action = Column(String(255), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



class LessonProgress(Base):
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