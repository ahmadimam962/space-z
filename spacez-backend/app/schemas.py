"""
Pydantic Schemas Module
هذا الموديول يعرّف كافة مخططات التحقق من البيانات (Data Validation Schemas).
تم تنظيمها حسب النطاق (Domain) لضمان سهولة الصيانة.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==========================================
# 1. Authentication Schemas
# ==========================================

class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)


class RegisterResponse(BaseModel):
    success: bool
    message: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)


class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    deviceId: str = Field(..., min_length=1)


class ResendOTPRequest(BaseModel):
    email: EmailStr


class GoogleLoginRequest(BaseModel):
    idToken: str = Field(..., min_length=1)
    deviceId: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6)


# ==========================================
# 2. User Schemas
# ==========================================

class CompletePhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class LogoutRequest(BaseModel):
    deviceId: str = Field(..., min_length=1)


# ==========================================
# 3. Course & Content Schemas
# ==========================================

class CourseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: int = Field(..., ge=0)
    thumbnail_url: Optional[str] = None
    status: str = Field(default="hidden", pattern="^(active|hidden)$")
    is_paid: bool = True
    is_featured: bool = False


class CourseUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    thumbnail_url: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|hidden)$")
    is_paid: Optional[bool] = None
    is_featured: Optional[bool] = None


class SectionCreateRequest(BaseModel):
    title: str
    sort_order: int = 1


class SectionUpdateRequest(BaseModel):
    title: Optional[str] = None
    sort_order: Optional[int] = None


class LessonCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    lesson_type: str = "video"
    video_provider: Optional[str] = None
    video_url: Optional[str] = None
    pdf_url: Optional[str] = None
    content_text: Optional[str] = None
    sort_order: int = 1
    is_free_preview: bool = False


class LessonUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    lesson_type: Optional[str] = None
    video_provider: Optional[str] = None
    video_url: Optional[str] = None
    pdf_url: Optional[str] = None
    content_text: Optional[str] = None
    sort_order: Optional[int] = None
    is_free_preview: Optional[bool] = None


# ==========================================
# 4. Payment & Enrollment Schemas
# ==========================================

class PaymentSettingCreateRequest(BaseModel):
    method_name: str = Field(..., min_length=1, max_length=100)
    account_name: Optional[str] = None
    account_number: str = Field(..., min_length=1)
    instructions: Optional[str] = None
    is_active: bool = True


class PaymentSettingUpdateRequest(BaseModel):
    method_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None


class PurchaseCourseRequest(BaseModel):
    course_id: int = Field(..., gt=0)
    transfer_number: str = Field(..., min_length=1)


class GrantCourseRequest(BaseModel):
    user_id: int
    course_id: int


class CouponCreateRequest(BaseModel):
    code: str
    discount_type: str = "percent"
    discount_value: int
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    is_active: bool = True


class CouponUpdateRequest(BaseModel):
    code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None


class PurchaseAdminNoteRequest(BaseModel):
    admin_note: str


class MarkLessonProgressRequest(BaseModel):
    lesson_id: int
    is_completed: bool = True

class RefreshTokenRequest(BaseModel):
    refresh_token: str