"""
Authentication Module
---------------------
This module handles all authentication-related operations including:

1. Registration Flow:
   - Register new users with email verification (OTP)
   - Resend OTP codes
   - Verify OTP and activate account

2. Login Flow:
   - Local login (email/phone + password)
   - Google OAuth login
   - Device management (max 2 devices per user)

3. Password Reset Flow:
   - Forgot password (send reset OTP)
   - Reset password with OTP verification

Security Features:
- OTP rate limiting (5 requests per 15 minutes)
- OTP cooldown (40 seconds between requests)
- OTP expiration (10 minutes)
- Device limit enforcement (max 2 devices)
- Password hashing with bcrypt
- JWT token-based authentication
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Local application imports
from app.config import settings
from app.database import get_db
from app.models import (
    User,
    OTPCode,
    PendingRegistration,
    UserDevice
)
from app.schemas import (
    RegisterRequest,
    VerifyOTPRequest,
    LoginRequest,
    ResendOTPRequest,
    GoogleLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    LogoutRequest
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    hash_otp,
    verify_otp_code
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


# ==========================================
# Helper Functions
# ==========================================

def can_send_otp(email: str, db: Session) -> None:
    """
    Check if an OTP can be sent to the given email address.
    
    Enforces two rate limiting rules:
    1. Cooldown: Must wait at least OTP_COOLDOWN_SECONDS since last OTP
    2. Rate limit: Maximum OTP_RATE_LIMIT_COUNT requests per OTP_RATE_LIMIT_MINUTES
    
    Args:
        email (str): The email address to check.
        db (Session): The database session.
        
    Raises:
        HTTPException: 429 if rate limit is exceeded.
    """
    now = datetime.utcnow()
    
    # 1. Check cooldown period
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
    
    # 2. Check rate limit window
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
    Create a new OTP code, save it to the database, and send it via email.
    
    This function:
    1. Marks all existing unused OTPs for this email as used (invalidates them)
    2. Generates a new 6-digit OTP code
    3. Hashes and saves the OTP to the database
    4. Sends the plain text OTP to the user's email
    
    Args:
        email (str): The email address to send the OTP to.
        db (Session): The database session.
    """
    # 1. Invalidate any existing unused OTPs for this email
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == "register",
        OTPCode.is_used == False
    ).update({
        OTPCode.is_used: True
    })
    
    # 2. Generate a new 6-digit OTP (100000-999999)
    otp_code = str(secrets.randbelow(900000) + 100000)
    
    # 3. Create and save the hashed OTP
    otp = OTPCode(
        email=email,
        code=hash_otp(otp_code),
        purpose="register",
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )
    
    db.add(otp)
    db.commit()
    
    # 4. Send the plain text OTP via email
    send_otp_email(email, otp_code)


def register_device_or_fail(user_id: int, device_id: str, db: Session) -> None:
    """
    Register a device for a user or fail if device limit is reached.
    
    Each user can have a maximum of 2 registered devices. If the limit is reached,
    the function raises an HTTP 403 error.
    
    Args:
        user_id (int): The ID of the user.
        device_id (str): The unique identifier for the device.
        db (Session): The database session.
        
    Raises:
        HTTPException: 403 if the device limit (2) is reached.
    """
    # Check if device is already registered
    existing_device = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id
    ).first()
    
    if existing_device:
        # Update last login timestamp
        existing_device.last_login_at = datetime.utcnow()
    else:
        # Check device limit
        device_count = db.query(UserDevice).filter(
            UserDevice.user_id == user_id
        ).count()
        
        if device_count >= 2:
            raise HTTPException(
                status_code=403,
                detail="Device limit reached. This account can only be used on 2 devices."
            )
        
        # Register new device
        db.add(UserDevice(
            user_id=user_id,
            device_id=device_id
        ))
    
    db.commit()


# ==========================================
# Registration Endpoints
# ==========================================

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new user account.
    
    Flow:
    1. Validate email and phone number are not already registered
    2. Check OTP rate limits
    3. Clear any existing pending registration for this email
    4. Create a pending registration with hashed password
    5. Generate and send OTP to the user's email
    
    Args:
        request (RegisterRequest): The registration data.
        db (Session): The database session.
        
    Returns:
        dict: Success message indicating OTP was sent.
        
    Raises:
        HTTPException: 400 if email or phone already exists.
        HTTPException: 429 if OTP rate limit is exceeded.
    """
    # 1. Check if email already exists
    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )
    
    # 2. Check if phone number already exists
    existing_phone = db.query(User).filter(
        User.phone_number == request.phone_number
    ).first()
    
    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone already exists"
        )
    
    # 3. Check OTP rate limits
    can_send_otp(request.email, db)
    
    # 4. Clear any existing pending registration for this email
    db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).delete()
    
    # 5. Create pending registration
    pending = PendingRegistration(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone_number=request.phone_number,
        password_hash=hash_password(request.password)
    )
    
    db.add(pending)
    db.commit()
    
    # 6. Generate and send OTP
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
    """
    Resend OTP to a user who is in the registration process.
    
    Args:
        request (ResendOTPRequest): The email address to resend OTP to.
        db (Session): The database session.
        
    Returns:
        dict: Success message indicating OTP was resent.
        
    Raises:
        HTTPException: 404 if no pending registration found for this email.
        HTTPException: 429 if OTP rate limit is exceeded.
    """
    # Check if pending registration exists
    pending = db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).first()
    
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Pending registration not found"
        )
    
    # Check OTP rate limits
    can_send_otp(request.email, db)
    
    # Generate and send new OTP
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
    Verify OTP and activate the user account.
    
    Flow:
    1. Find all unused OTPs for this email
    2. Verify the OTP code against each (supports multiple attempts)
    3. Check if OTP has expired
    4. Fetch the pending registration
    5. Create the user account
    6. Mark OTP as used and delete pending registration
    
    Args:
        request (VerifyOTPRequest): The email and OTP code to verify.
        db (Session): The database session.
        
    Returns:
        dict: Success message and user data.
        
    Raises:
        HTTPException: 400 if OTP is invalid or expired.
        HTTPException: 404 if no pending registration found.
    """
    # 1. Fetch all unused OTPs for this email
    otp_records = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == "register",
        OTPCode.is_used == False
    ).order_by(
        OTPCode.created_at.desc()
    ).all()
    
    # 2. Verify OTP code
    otp_record = None
    
    for record in otp_records:
        if verify_otp_code(request.otp, record.code):
            otp_record = record
            break
    
    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )
    
    # 3. Check if OTP has expired
    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )
    
    # 4. Fetch pending registration
    pending = db.query(PendingRegistration).filter(
        PendingRegistration.email == request.email
    ).first()
    
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Pending registration not found"
        )
    
    # 5. Double-check email doesn't exist (race condition protection)
    existing_user = db.query(User).filter(
        User.email == pending.email
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )
    
    # 6. Create the user account
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
    
    # 7. Mark OTP as used
    otp_record.is_used = True
    
    # 8. Delete pending registration
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
    Authenticate a user with email/phone and password.
    
    Flow:
    1. Find user by email or phone number
    2. Validate user account (local auth, email verified, not banned)
    3. Verify password
    4. Register or update device
    5. Generate and return JWT token
    
    Args:
        request (LoginRequest): The login credentials and device ID.
        db (Session): The database session.
        
    Returns:
        dict: Success message, JWT token, and user data.
        
    Raises:
        HTTPException: 401 if credentials are invalid.
        HTTPException: 400 if account uses Google login.
        HTTPException: 403 if email not verified or account banned.
        HTTPException: 403 if device limit reached.
    """
    # 1. Find user by email or phone
    user = db.query(User).filter(
        (User.email == request.identifier) |
        (User.phone_number == request.identifier)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    # 2. Validate account type and status
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
    
    # 3. Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    # 4. Register or update device
    register_device_or_fail(user.id, request.deviceId, db)
    
    # 5. Generate JWT token
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
    Authenticate a user with Google OAuth.
    
    Flow:
    1. Verify Google ID token
    2. Extract user info from token payload
    3. Find or create user account
    4. Register or update device
    5. Generate and return JWT token
    
    Args:
        request (GoogleLoginRequest): The Google ID token and device ID.
        db (Session): The database session.
        
    Returns:
        dict: Success message, JWT token, phone requirement flag, and user data.
        
    Raises:
        HTTPException: 401 if Google token is invalid.
        HTTPException: 400 if Google account has no email.
        HTTPException: 403 if account is banned or device limit reached.
    """
    # 1. Verify Google ID token
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
    
    # 2. Extract user info
    email = payload.get("email")
    first_name = payload.get("given_name") or "Google"
    last_name = payload.get("family_name") or "User"
    
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Google account has no email"
        )
    
    # 3. Find or create user
    user = db.query(User).filter(
        User.email == email
    ).first()
    
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
    
    # 4. Validate account status
    if user.is_banned:
        raise HTTPException(
            status_code=403,
            detail="Account is banned"
        )
    
    # 5. Register or update device
    register_device_or_fail(user.id, request.deviceId, db)
    
    # 6. Generate JWT token
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
    Initiate password reset flow by sending a reset OTP.
    
    Flow:
    1. Find user by email
    2. Validate account uses local authentication
    3. Check OTP rate limits
    4. Invalidate existing unused reset OTPs
    5. Generate and send new reset OTP
    
    Note: For security, this endpoint returns success even if email doesn't exist
    to prevent email enumeration attacks.
    
    Args:
        request (ForgotPasswordRequest): The email address to send reset code to.
        db (Session): The database session.
        
    Returns:
        dict: Success message (always returns success for security).
        
    Raises:
        HTTPException: 400 if account uses Google login.
        HTTPException: 429 if OTP rate limit is exceeded.
    """
    # 1. Find user
    user = db.query(User).filter(
        User.email == request.email
    ).first()
    
    if not user:
        # Return success even if email doesn't exist (security)
        return {
            "success": True,
            "message": "If this email exists, a reset code has been sent"
        }
    
    # 2. Validate account type
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login"
        )
    
    # 3. Check OTP rate limits (with cooldown)
    now = datetime.utcnow()
    
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
    
    # 4. Invalidate existing unused reset OTPs
    db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE,
        OTPCode.is_used == False
    ).update({
        OTPCode.is_used: True
    })
    
    # 5. Generate and send new reset OTP
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
    Reset user's password using OTP verification.
    
    Flow:
    1. Find user by email
    2. Validate account uses local authentication
    3. Find all unused reset OTPs for this email
    4. Verify the OTP code
    5. Check if OTP has expired
    6. Update password and mark OTP as used
    
    Args:
        request (ResetPasswordRequest): The email, OTP, and new password.
        db (Session): The database session.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException: 400 if reset request is invalid or account uses Google login.
        HTTPException: 400 if OTP is invalid or expired.
    """
    # 1. Find user
    user = db.query(User).filter(
        User.email == request.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset request"
        )
    
    # 2. Validate account type
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login"
        )
    
    # 3. Fetch all unused reset OTPs
    otp_records = db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.purpose == PASSWORD_RESET_PURPOSE,
        OTPCode.is_used == False
    ).order_by(
        OTPCode.created_at.desc()
    ).all()
    
    # 4. Verify OTP code
    otp_record = None
    
    for record in otp_records:
        if verify_otp_code(request.otp, record.code):
            otp_record = record
            break
    
    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )
    
    # 5. Check if OTP has expired
    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )
    
    # 6. Update password and mark OTP as used
    user.password_hash = hash_password(request.new_password)
    otp_record.is_used = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Password reset successfully"
    }

# ==========================================
# logout Reset Endpoints
# ==========================================

@router.post("/logout")
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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