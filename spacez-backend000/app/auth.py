"""
Authentication Module
هذا الموديول يعالج كافة عمليات المصادقة بما في ذلك:

تدفق التسجيل:
- تسجيل مستخدمين جدد مع التحقق من البريد (OTP)
- إعادة إرسال رموز OTP
- التحقق من OTP وتفعيل الحساب

تدفق تسجيل الدخول:
- تسجيل الدخول المحلي (بريد/هاتف + كلمة مرور)
- تسجيل الدخول عبر Google OAuth
- إدارة الأجهزة (حد أقصى جهازين لكل مستخدم)

تدفق إعادة تعيين كلمة المرور:
- نسيت كلمة المرور (إرسال OTP لإعادة التعيين)
- إعادة تعيين كلمة المرور مع التحقق من OTP

مميزات الأمان:
- Rate limiting لـ OTP (5 طلبات كل 15 دقيقة)
- Cooldown لـ OTP (40 ثانية بين الطلبات)
- انتهاء صلاحية OTP (10 دقائق)
- فرض حد الأجهزة (حد أقصى 2)
- تشفير كلمات المرور باستخدام bcrypt
- مصادقة مبنية على JWT tokens
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Local imports
from app.config import settings
from app.database import get_db
from app.models import User, OTPCode, PendingRegistration, UserDevice
from app.schemas import (
    RegisterRequest, VerifyOTPRequest, LoginRequest,
    ResendOTPRequest, GoogleLoginRequest,
    ForgotPasswordRequest, ResetPasswordRequest, LogoutRequest
)
from app.security import (
    hash_password, verify_password, create_access_token,
    hash_otp, verify_otp_code
)
from app.email_service import send_otp_email
from app.users import get_current_user


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# ==========================================
# Constants
# ==========================================
OTP_COOLDOWN_SECONDS = 40
OTP_RATE_LIMIT_COUNT = 5
OTP_RATE_LIMIT_MINUTES = 15
OTP_EXPIRE_MINUTES = 10
PASSWORD_RESET_PURPOSE = "password_reset"

LOGIN_RATE_LIMIT_COUNT = 10
LOGIN_RATE_LIMIT_MINUTES = 15

login_attempts = {}


# ==========================================
# Helper Functions
# ==========================================

def can_send_otp(email: str, db: Session) -> None:
    """
    التحقق من إمكانية إرسال OTP للبريد المعطى.
    يفرض قاعدتين لتحديد المعدل:
    1. Cooldown: يجب الانتظار على الأقل OTP_COOLDOWN_SECONDS منذ آخر OTP
    2. Rate limit: حد أقصى OTP_RATE_LIMIT_COUNT طلبات كل OTP_RATE_LIMIT_MINUTES
    """
    now = datetime.utcnow()

    # 1. التحقق من فترة الـ cooldown
    last_otp = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == "register"
    ).order_by(
        OTPCode.created_at.desc()
    ).first()

    if last_otp:
        seconds_since_last = (now - last_otp.created_at).total_seconds()

        if seconds_since_last < OTP_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {int(OTP_COOLDOWN_SECONDS - seconds_since_last)} seconds before requesting another OTP"
            )

    # 2. التحقق من نافذة rate limit
    window_start = now - timedelta(minutes=OTP_RATE_LIMIT_MINUTES)

    otp_count = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == "register",
        OTPCode.created_at >= window_start
    ).count()

    if otp_count >= OTP_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again later."
        )


def create_and_send_otp(email: str, db: Session) -> None:
    """
    إنشاء رمز OTP جديد، حفظه في قاعدة البيانات، وإرساله عبر البريد.
    تقوم هذه الدالة بـ:
    1. تعليم كل OTPs غير المستخدمة الموجودة لهذا البريد كمستخدمة (إبطالها)
    2. توليد رمز OTP جديد من 6 أرقام
    3. تشفير وحفظ OTP في قاعدة البيانات
    4. إرسال OTP النصي إلى بريد المستخدم
    """
    # 1. إبطال أي OTPs غير مستخدمة موجودة لهذا البريد
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == "register",
        OTPCode.is_used == False
    ).update({
        OTPCode.is_used: True
    })

    # 2. توليد OTP جديد من 6 أرقام (100000-999999)
    otp_code = str(secrets.randbelow(900000) + 100000)

    # 3. إنشاء وحفظ OTP المشفر
    otp = OTPCode(
        email=email,
        code=hash_otp(otp_code),
        purpose="register",
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )

    db.add(otp)
    db.commit()

    # 4. إرسال OTP النصي عبر البريد
    send_otp_email(email, otp_code)


def register_device_or_fail(user_id: int, device_id: str, db: Session) -> None:
    """
    تسجيل جهاز للمستخدم أو الفشل إذا تم الوصول إلى حد الأجهزة.
    كل مستخدم يمكنه الحصول على حد أقصى 2 أجهزة مسجلة.
    """
    existing_device = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id
    ).first()

    if existing_device:
        # تحديث وقت آخر تسجيل دخول
        existing_device.last_login_at = datetime.utcnow()
    else:
        # التحقق من حد الأجهزة
        device_count = db.query(UserDevice).filter(
            UserDevice.user_id == user_id
        ).count()

        if device_count >= 2:
            raise HTTPException(
                status_code=403,
                detail="Device limit reached. This account can only be used on 2 devices."
            )

        # تسجيل جهاز جديد
        db.add(UserDevice(
            user_id=user_id,
            device_id=device_id
        ))

    db.commit()

def check_login_rate_limit(identifier: str):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=LOGIN_RATE_LIMIT_MINUTES)

    attempts = login_attempts.get(identifier, [])
    attempts = [t for t in attempts if t >= window_start]

    if len(attempts) >= LOGIN_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later."
        )

    attempts.append(now)
    login_attempts[identifier] = attempts
# ==========================================
# Registration Endpoints
# ==========================================

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    تسجيل حساب مستخدم جديد.
    التدفق:
    1. التحقق من أن البريد ورقم الهاتف غير مسجلين مسبقاً
    2. التحقق من حدود معدل OTP
    3. مسح أي تسجيل معلق موجود لهذا البريد
    4. إنشاء تسجيل معلق مع كلمة مرور مشفرة
    5. توليد وإرسال OTP إلى بريد المستخدم
    """
    # 1. التحقق من وجود البريد
    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # 2. التحقق من وجود رقم الهاتف
    existing_phone = db.query(User).filter(
        User.phone_number == request.phone_number
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone already exists"
        )

    # 3. التحقق من حدود معدل OTP
    can_send_otp(request.email, db)

    # 4. مسح أي تسجيل معلق موجود لهذا البريد
    db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).delete()

    # 5. إنشاء التسجيل المعلق
    pending = PendingRegistration(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone_number=request.phone_number,
        password_hash=hash_password(request.password)
    )

    db.add(pending)
    db.commit()

    # 6. توليد وإرسال OTP
    create_and_send_otp(request.email, db)

    return {
        "success": True,
        "message": "OTP sent successfully"
    }


@router.post("/resend-otp")
def resend_otp(
    request: ResendOTPRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """إعادة إرسال OTP لمستخدم في عملية التسجيل."""
    pending = db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).first()

    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Pending registration not found"
        )

    can_send_otp(request.email, db)
    create_and_send_otp(request.email, db)

    return {
        "success": True,
        "message": "OTP resent successfully"
    }


@router.post("/verify-otp")
def verify_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    التحقق من OTP وتفعيل حساب المستخدم.
    التدفق:
    1. إيجاد كل OTPs غير المستخدمة لهذا البريد
    2. التحقق من رمز OTP مقابل كل منها
    3. التحقق من انتهاء صلاحية OTP
    4. جلب التسجيل المعلق
    5. إنشاء حساب المستخدم
    6. تعليم OTP كمستخدمة وحذف التسجيل المعلق
    """
    # 1. جلب كل OTPs غير المستخدمة لهذا البريد
    otp_records = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == "register",
        OTPCode.is_used == False
    ).order_by(
        OTPCode.created_at.desc()
    ).all()

    # 2. التحقق من رمز OTP
    otp_record = None

    for record in otp_records:
        if verify_otp_code(request.otp, record.code):
            otp_record = record
            break

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # 3. التحقق من انتهاء صلاحية OTP
    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    # 4. جلب التسجيل المعلق
    pending = db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).first()

    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Pending registration not found"
        )

    # 5. تحقق مزدوج من عدم وجود البريد (حماية من race condition)
    existing_user = db.query(User).filter(
        User.email == pending.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # 6. إنشاء حساب المستخدم
    user = User(
        first_name=pending.first_name,
        last_name=pending.last_name,
        email=pending.email,
        phone_number=pending.phone_number,
        password_hash=pending.password_hash,
        role="student",
        auth_provider="local",
        is_email_verified=True,
        is_banned=False
    )

    db.add(user)

    # 7. تعليم OTP كمستخدمة
    otp_record.is_used = True

    # 8. حذف التسجيل المعلق
    db.delete(pending)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Account verified successfully",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role
        }
    }


# ==========================================
# Login Endpoints
# ==========================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    مصادقة مستخدم بالبريد/الهاتف وكلمة المرور.
    التدفق:
    1. إيجاد المستخدم بالبريد أو رقم الهاتف
    2. التحقق من صحة الحساب (local auth, بريد موثق، غير محظور)
    3. التحقق من كلمة المرور
    4. تسجيل أو تحديث الجهاز
    5. توليد وإرجاع JWT token
    """

    check_login_rate_limit(request.identifier)

    # 1. إيجاد المستخدم بالبريد أو الهاتف
    user = db.query(User).filter(
        (User.email == request.identifier) |
        (User.phone_number == request.identifier)
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # 2. التحقق من نوع الحساب وحالته
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="Please login with Google"
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified"
        )

    if user.is_banned:
        raise HTTPException(
            status_code=403,
            detail="Account is banned"
        )

    # 3. التحقق من كلمة المرور
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # 4. تسجيل أو تحديث الجهاز
    register_device_or_fail(user.id, request.deviceId, db)

    # 5. توليد JWT token
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "phoneNumber": user.phone_number,
            "role": user.role
        }
    }


@router.post("/google-login")
def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    مصادقة مستخدم عبر Google OAuth.
    التدفق:
    1. التحقق من Google ID token
    2. استخراج معلومات المستخدم من payload
    3. إيجاد أو إنشاء حساب المستخدم
    4. تسجيل أو تحديث الجهاز
    5. توليد وإرجاع JWT token
    """
    # 1. التحقق من Google ID token
    try:
        payload = id_token.verify_oauth2_token(
            request.idToken,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token"
        )

    # 2. استخراج معلومات المستخدم
    email = payload.get("email")
    first_name = payload.get("given_name") or "Google"
    last_name = payload.get("family_name") or "User"

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Google account has no email"
        )

    # 3. إيجاد أو إنشاء المستخدم
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=None,
            password_hash=None,
            role="student",
            auth_provider="google",
            is_email_verified=True,
            is_banned=False
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. التحقق من حالة الحساب
    if user.is_banned:
        raise HTTPException(
            status_code=403,
            detail="Account is banned"
        )

    # 5. تسجيل أو تحديث الجهاز
    register_device_or_fail(user.id, request.deviceId, db)

    # 6. توليد JWT token
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "success": True,
        "message": "Google login successful",
        "token": token,
        "requiresPhoneNumber": user.phone_number is None,
        "user": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "phoneNumber": user.phone_number,
            "role": user.role
        }
    }


# ==========================================
# Password Reset Endpoints
# ==========================================

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    بدء تدفق إعادة تعيين كلمة المرور بإرسال OTP.
    ملاحظة: للأمان، هذا الـ endpoint يُرجع success حتى لو البريد غير موجود
    لمنع هجمات enumeration.
    """
    # 1. إيجاد المستخدم
    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        # إرجاع success حتى لو البريد غير موجود (للأمان)
        return {
            "success": True,
            "message": "If this email exists, a reset code has been sent"
        }

    # 2. التحقق من نوع الحساب
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login"
        )

    # 3. التحقق من حدود معدل OTP (مع cooldown)
    now = datetime.utcnow()

    window_start = now - timedelta(minutes=OTP_RATE_LIMIT_MINUTES)

    otp_count = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE,
        OTPCode.created_at >= window_start
    ).count()

    if otp_count >= OTP_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Please try again later."
        )

    last_otp = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE
    ).order_by(
        OTPCode.created_at.desc()
    ).first()

    if last_otp:
        seconds_since_last = (now - last_otp.created_at).total_seconds()
        if seconds_since_last < OTP_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {int(OTP_COOLDOWN_SECONDS - seconds_since_last)} seconds before requesting another code"
            )

    # 4. إبطال OTPs غير المستخدمة الموجودة
    db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE,
        OTPCode.is_used == False
    ).update({
        OTPCode.is_used: True
    })

    # 5. توليد وإرسال OTP جديد
    otp_code = str(secrets.randbelow(900000) + 100000)

    otp = OTPCode(
        email=request.email,
        code=hash_otp(otp_code),
        purpose=PASSWORD_RESET_PURPOSE,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )

    db.add(otp)
    db.commit()

    send_otp_email(request.email, otp_code)

    return {
        "success": True,
        "message": "Password reset code sent"
    }


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    إعادة تعيين كلمة مرور المستخدم باستخدام التحقق من OTP.
    التدفق:
    1. إيجاد المستخدم بالبريد
    2. التحقق من أن الحساب يستخدم مصادقة محلية
    3. إيجاد كل OTPs غير المستخدمة لإعادة التعيين
    4. التحقق من رمز OTP
    5. التحقق من انتهاء الصلاحية
    6. تحديث كلمة المرور وتعليم OTP كمستخدمة
    """
    # 1. إيجاد المستخدم
    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset request"
        )

    # 2. التحقق من نوع الحساب
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login"
        )

    # 3. جلب كل OTPs غير المستخدمة لإعادة التعيين
    otp_records = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE,
        OTPCode.is_used == False
    ).order_by(
        OTPCode.created_at.desc()
    ).all()

    # 4. التحقق من رمز OTP
    otp_record = None

    for record in otp_records:
        if verify_otp_code(request.otp, record.code):
            otp_record = record
            break

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # 5. التحقق من انتهاء صلاحية OTP
    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    # 6. تحديث كلمة المرور وتعليم OTP كمستخدمة
    user.password_hash = hash_password(request.new_password)
    otp_record.is_used = True

    db.commit()

    return {
        "success": True,
        "message": "Password reset successfully"
    }


# ==========================================
# Logout Endpoint
# ==========================================

@router.post("/logout")
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تسجيل خروج المستخدم من جهاز محدد."""
    device = db.query(UserDevice).filter(
        UserDevice.user_id == current_user.id,
        UserDevice.device_id == request.deviceId
    ).first()

    if device:
        db.delete(device)
        db.commit()

    return {
        "success": True,
        "message": "Logged out successfully"
    }