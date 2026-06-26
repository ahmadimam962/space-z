"""
Security Module
---------------
This module handles all security-related operations including:
- Password hashing and verification
- JWT token creation and decoding
- OTP (One-Time Password) hashing and verification

All cryptographic operations use industry-standard libraries (passlib, python-jose).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings


# ==========================================
# Password Hashing Context Initialization
# ==========================================

# Initialize passlib context with bcrypt algorithm for secure password hashing
# "deprecated=auto" automatically handles migration to newer hashing algorithms in the future
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ==========================================
# Password Operations
# ==========================================

def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password (str): The plain text password to hash.
        
    Returns:
        str: The hashed password string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hashed version.
    
    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The stored hashed password.
        
    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ==========================================
# JWT Token Operations
# ==========================================

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT access token with an expiration time.
    
    Args:
        data (dict): The payload data to encode in the token.
        
    Returns:
        str: The encoded JWT token string.
        
    Note:
        The expiration time is calculated based on settings.ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    # Create a copy to avoid mutating the original data
    to_encode = data.copy()
    
    # Calculate expiration time
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    # Add expiration to payload
    to_encode.update({
        "exp": expire
    })
    
    # Encode and return the JWT token
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token (str): The JWT token to decode.
        
    Returns:
        Optional[dict]: The decoded payload if valid, None if invalid or expired.
    """
    try:
        # Decode the token using the secret key and algorithm
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        # Return None if token is invalid, expired, or malformed
        return None


# ==========================================
# OTP Operations
# ==========================================

def hash_otp(otp: str) -> str:
    """
    Hash an OTP (One-Time Password) for secure storage.
    
    Args:
        otp (str): The plain text OTP to hash.
        
    Returns:
        str: The hashed OTP string.
    """
    return pwd_context.hash(otp)


def verify_otp_code(plain_otp: str, hashed_otp: str) -> bool:
    """
    Verify a plain text OTP against its hashed version.
    
    Args:
        plain_otp (str): The plain text OTP to verify.
        hashed_otp (str): The stored hashed OTP.
        
    Returns:
        bool: True if the OTP matches, False otherwise.
    """
    return pwd_context.verify(plain_otp, hashed_otp)