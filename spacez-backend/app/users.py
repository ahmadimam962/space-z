"""
User Management Router
----------------------
This module handles user-related API endpoints.
It includes functionalities for fetching the user's profile and 
updating/completing their phone number.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any

# Local application imports
from app.database import get_db
from app.models import User
from app.security import decode_access_token,verify_password,hash_password
from app.schemas import CompletePhoneRequest,ChangePasswordRequest

# ==========================================
# Router & Security Initialization
# ==========================================

# Initialize the APIRouter with a specific prefix and tags for Swagger UI documentation
router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)

# Initialize HTTPBearer security scheme to enforce Bearer Token authentication in Swagger
security = HTTPBearer()


# ==========================================
# Dependencies
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract, validate, and fetch the current authenticated user.
    
    Steps:
    1. Extracts the Bearer token from the request headers.
    2. Decodes the token to get the payload.
    3. Validates the payload and extracts the user ID.
    4. Queries the database to fetch the user.
    5. Checks if the user exists and is not banned.
    
    Returns:
        User: The authenticated SQLAlchemy User object.
        
    Raises:
        HTTPException: 401 if token is invalid/expired or payload is missing 'sub'.
        HTTPException: 404 if the user is not found in the database.
        HTTPException: 403 if the user's account is banned.
    """
    # 1. Extract token from credentials
    token = credentials.credentials
    payload = decode_access_token(token)

    # 2. Validate token payload
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    # 3. Extract user ID from payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )

    # 4. Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # 5. Check if user is banned
    if user.is_banned:
        raise HTTPException(
            status_code=403,
            detail="Account is banned"
        )

    return user


# ==========================================
# Endpoints
# ==========================================

@router.get("/profile")
def profile(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Fetch the authenticated user's profile information.
    
    Returns:
        dict: A dictionary containing the user's basic profile details.
    """
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "email": current_user.email,
            "phoneNumber": current_user.phone_number,
            "role": current_user.role
        }
    }


@router.post("/complete-phone")
def complete_phone(
    request: CompletePhoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update or complete the authenticated user's phone number.
    
    Args:
        request (CompletePhoneRequest): The new phone number data.
        current_user (User): The authenticated user (injected via dependency).
        db (Session): The database session (injected via dependency).
        
    Returns:
        dict: Success message and the updated user data.
        
    Raises:
        HTTPException: 400 if the phone number is already registered to another user.
    """
    # Check if the phone number is already used by another user
    existing_phone = db.query(User).filter(
        User.phone_number == request.phone_number,
        User.id != current_user.id  # Ensure we don't flag the current user's own number
    ).first()
    
    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone already exists"
        )

    # Update the phone number and commit the transaction to the database
    current_user.phone_number = request.phone_number
    db.commit()

    # Optional: Refresh the user instance to ensure we have the latest DB state
    # db.refresh(current_user) 

    return {
        "success": True,
        "message": "Phone number updated successfully",
        "data": {
            "id": current_user.id,
            "phoneNumber": current_user.phone_number
        }
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.auth_provider != "local":
        raise HTTPException(
            status_code=400,
            detail="Google accounts cannot change password"
        )

    if not verify_password(
        request.current_password,
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    current_user.password_hash = hash_password(
        request.new_password
    )

    db.commit()

    return {
        "success": True,
        "message": "Password changed successfully"
    }