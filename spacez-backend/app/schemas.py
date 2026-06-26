"""
Pydantic Schemas Module
-----------------------
This module defines all the data validation schemas used across the application.
Schemas are organized by feature/domain for better maintainability:

1. Authentication Schemas (Register, Login, OTP, Password Reset)
2. User Schemas (Profile, Phone Completion)
3. Course Schemas (Create, Update)
4. Payment Schemas (Settings, Purchases)

All schemas inherit from Pydantic's BaseModel for automatic validation and serialization.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==========================================
# Authentication Schemas
# ==========================================

class RegisterRequest(BaseModel):
    """
    Schema for user registration request.
    
    Attributes:
        first_name: User's first name.
        last_name: User's last name.
        email: User's email address (validated).
        phone_number: User's phone number.
        password: User's plain text password (will be hashed server-side).
    """
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)


class RegisterResponse(BaseModel):
    """
    Schema for registration response.
    
    Attributes:
        success: Whether the registration was successful.
        message: A message describing the result (e.g., "OTP sent to email").
    """
    success: bool
    message: str


class VerifyOTPRequest(BaseModel):
    """
    Schema for OTP verification request.
    
    Attributes:
        email: The email address associated with the OTP.
        otp: The one-time password code to verify.
    """
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)


class LoginRequest(BaseModel):
    """
    Schema for user login request.
    
    Attributes:
        identifier: Email or phone number used for login.
        password: User's plain text password.
        deviceId: Unique identifier for the user's device (for session management).
    """
    identifier: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    deviceId: str = Field(..., min_length=1)


class ResendOTPRequest(BaseModel):
    """
    Schema for requesting a new OTP to be sent.
    
    Attributes:
        email: The email address to resend the OTP to.
    """
    email: EmailStr


class GoogleLoginRequest(BaseModel):
    """
    Schema for Google OAuth login request.
    
    Attributes:
        idToken: The Google ID token received from the client.
        deviceId: Unique identifier for the user's device.
    """
    idToken: str = Field(..., min_length=1)
    deviceId: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """
    Schema for initiating the password reset flow.
    
    Attributes:
        email: The email address to send the reset OTP to.
    """
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """
    Schema for resetting the password with OTP verification.
    
    Attributes:
        email: The user's email address.
        otp: The OTP received for password reset.
        new_password: The new password to set.
    """
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6)


# ==========================================
# User Schemas
# ==========================================

class CompletePhoneRequest(BaseModel):
    """
    Schema for completing/updating the user's phone number.
    
    Attributes:
        phone_number: The new phone number to set.
    """
    phone_number: str = Field(..., min_length=10, max_length=15)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class LogoutRequest(BaseModel):
    deviceId: str = Field(..., min_length=1)

# ==========================================
# Course Schemas
# ==========================================

class CourseCreateRequest(BaseModel):
    """
    Schema for creating a new course.
    
    Attributes:
        title: The course title.
        description: Optional detailed description of the course.
        price: Course price in the smallest currency unit (e.g., cents).
        thumbnail_url: Optional URL for the course thumbnail image.
        status: Course visibility status ("hidden", "published", etc.).
        is_paid: Whether the course requires payment to access.
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: int = Field(..., ge=0)
    thumbnail_url: Optional[str] = None
    status: str = Field(default="hidden", pattern="^(active|hidden)$")
    is_paid: bool = True
    is_featured: bool = False


class CourseUpdateRequest(BaseModel):
    """
    Schema for updating an existing course (partial updates supported).
    
    All fields are optional to allow partial updates.
    """
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    thumbnail_url: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|hidden)$")
    is_paid: Optional[bool] = None
    is_featured: bool | None = None


# ==========================================
# Payment Schemas
# ==========================================

class PaymentSettingCreateRequest(BaseModel):
    """
    Schema for creating a new payment method setting.
    
    Attributes:
        method_name: Name of the payment method (e.g., "Bank Transfer", "PayPal").
        account_name: Optional name of the account holder.
        account_number: The account number or identifier.
        instructions: Optional instructions for the customer.
        is_active: Whether this payment method is currently active.
    """
    method_name: str = Field(..., min_length=1, max_length=100)
    account_name: Optional[str] = None
    account_number: str = Field(..., min_length=1)
    instructions: Optional[str] = None
    is_active: bool = True


class PaymentSettingUpdateRequest(BaseModel):
    """
    Schema for updating an existing payment method setting (partial updates supported).
    
    All fields are optional to allow partial updates.
    """
    method_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None


class PurchaseCourseRequest(BaseModel):
    """
    Schema for purchasing a course via manual payment verification.
    
    Attributes:
        course_id: The ID of the course to purchase.
        transfer_number: The transaction/transfer reference number from the payment.
    """
    course_id: int = Field(..., gt=0)
    transfer_number: str = Field(..., min_length=1)


class SectionCreateRequest(BaseModel):
    title: str
    sort_order: int = 1


class SectionUpdateRequest(BaseModel):
    title: str | None = None
    sort_order: int | None = None


class LessonCreateRequest(BaseModel):
    title: str
    description: str | None = None
    lesson_type: str = "video"
    video_provider: str | None = None
    video_url: str | None = None
    pdf_url: str | None = None
    content_text: str | None = None
    sort_order: int = 1
    is_free_preview: bool = False


class LessonUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    lesson_type: str | None = None
    video_provider: str | None = None
    video_url: str | None = None
    pdf_url: str | None = None
    content_text: str | None = None
    sort_order: int | None = None
    is_free_preview: bool | None = None


class GrantCourseRequest(BaseModel):
    user_id: int
    course_id: int


class GrantCourseRequest(BaseModel):
    user_id: int
    course_id: int




class CouponCreateRequest(BaseModel):
    code: str
    discount_type: str = "percent"
    discount_value: int
    max_uses: int | None = None
    expires_at: str | None = None
    is_active: bool = True


class CouponUpdateRequest(BaseModel):
    code: str | None = None
    discount_type: str | None = None
    discount_value: int | None = None
    max_uses: int | None = None
    expires_at: str | None = None
    is_active: bool | None = None


class PurchaseAdminNoteRequest(BaseModel):
    admin_note: str