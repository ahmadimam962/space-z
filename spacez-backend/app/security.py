"""
Security Module
هذا الموديول يعالج كل العمليات الأمنية بما في ذلك:
- تشفير كلمات المرور والتحقق منها
- إنشاء وفك رموز JWT tokens
- تشفير والتحقق من OTP
جميع العمليات التشفيرية تستخدم مكتبات معيارية (passlib, python-jose).
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings


# ==========================================
# Password Hashing Context Initialization
# ==========================================
# تهيئة passlib باستخدام خوارزمية bcrypt
# deprecated="auto" يتولى الترقية التلقائية للخوارزميات مستقبلاً
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ==========================================
# Password Operations
# ==========================================

def hash_password(password: str) -> str:
    """تشفير كلمة مرور نصية باستخدام bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """التحقق من تطابق كلمة المرور النصية مع النسخة المشفرة."""
    return pwd_context.verify(plain_password, hashed_password)


# ==========================================
# JWT Token Operations
# ==========================================

def create_access_token(data: Dict[str, Any]) -> str:
    """
    إنشاء JWT access token مع وقت انتهاء صلاحية.
    يتم حساب وقت الانتهاء بناءً على settings.ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    فك وتشفير JWT access token.
    يُرجع None في حال كان التوكن غير صالح أو منتهي الصلاحية.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ==========================================
# OTP Operations
# ==========================================

def hash_otp(otp: str) -> str:
    """تشفير OTP للتخزين الآمن."""
    return pwd_context.hash(otp)


def verify_otp_code(plain_otp: str, hashed_otp: str) -> bool:
    """التحقق من تطابق OTP النصي مع النسخة المشفرة."""
    return pwd_context.verify(plain_otp, hashed_otp)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)