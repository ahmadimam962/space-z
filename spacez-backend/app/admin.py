"""
Admin Module
------------
This module handles all admin-related operations including:

1. Admin Authentication:
   - get_current_admin dependency (role-based access control)

2. Dashboard Endpoints:
   - System statistics (users, students, admins, banned, auth providers)

3. User Management Endpoints:
   - List users (with search, filters, pagination)
   - Get user details (with device history)
   - Ban/unban users
   - Delete users (with device cleanup)
   - Remove user devices

All admin endpoints require authentication with "admin" role.
"""

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Local application imports
from app.database import get_db
from app.models import User, UserDevice
from app.users import get_current_user


# ==========================================
# Router Initialization
# ==========================================

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


# ==========================================
# Dependencies
# ==========================================

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to verify the current user has admin privileges.
    
    This dependency chains with get_current_user to:
    1. Validate the JWT token
    2. Fetch the user from the database
    3. Check if the user's role is "admin"
    
    Args:
        current_user (User): The authenticated user (injected via get_current_user).
        
    Returns:
        User: The authenticated admin user.
        
    Raises:
        HTTPException: 403 if the user's role is not "admin".
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user


# ==========================================
# Dashboard Endpoints
# ==========================================

@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Fetch system-wide statistics for the admin dashboard.
    
    Returns counts for:
    - Total users
    - Total students
    - Total admins
    - Banned users
    - Google OAuth users
    - Local authentication users
    
    Args:
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: A success flag and a dictionary of statistics.
    """
    # Fetch all statistics in separate queries
    # (could be optimized with a single query using CASE WHEN, but this is clearer)
    total_users = db.query(User).count()
    
    total_students = db.query(User).filter(
        User.role == "student"
    ).count()
    
    total_admins = db.query(User).filter(
        User.role == "admin"
    ).count()
    
    banned_users = db.query(User).filter(
        User.is_banned.is_(True)  # Best practice: use .is_(True) instead of == True
    ).count()
    
    google_users = db.query(User).filter(
        User.auth_provider == "google"
    ).count()
    
    local_users = db.query(User).filter(
        User.auth_provider == "local"
    ).count()
    
    return {
        "success": True,
        "data": {
            "totalUsers": total_users,
            "totalStudents": total_students,
            "totalAdmins": total_admins,
            "bannedUsers": banned_users,
            "googleUsers": google_users,
            "localUsers": local_users
        }
    }


# ==========================================
# User Management Endpoints
# ==========================================

@router.get("/users")
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_banned: Optional[bool] = None,
    auth_provider: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    List users with optional search, filters, and pagination.
    
    Supports:
    - Search by name, email, or phone number (case-insensitive partial match)
    - Filter by role (student/admin)
    - Filter by ban status (banned/unbanned)
    - Filter by auth provider (local/google)
    - Pagination with limit and offset
    
    Args:
        search (Optional[str]): Search term for name/email/phone.
        role (Optional[str]): Filter by user role.
        is_banned (Optional[bool]): Filter by ban status.
        auth_provider (Optional[str]): Filter by authentication provider.
        limit (int): Maximum number of users to return (default: 50).
        offset (int): Number of users to skip (default: 0).
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: A success flag, total count, and list of users.
    """
    # 1. Build the base query
    query = db.query(User)
    
    # 2. Apply search filter (case-insensitive partial match on multiple fields)
    if search:
        query = query.filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone_number.ilike(f"%{search}%")
            )
        )
    
    # 3. Apply role filter
    if role:
        query = query.filter(User.role == role)
    
    # 4. Apply ban status filter
    if is_banned is not None:
        query = query.filter(User.is_banned == is_banned)
    
    # 5. Apply auth provider filter
    if auth_provider:
        query = query.filter(User.auth_provider == auth_provider)
    
    # 6. Get total count (before pagination)
    total = query.count()
    
    # 7. Apply pagination and ordering (newest first)
    users = query.order_by(
        User.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "data": [
            {
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "phoneNumber": user.phone_number,
                "role": user.role,
                "authProvider": user.auth_provider,
                "isEmailVerified": user.is_email_verified,
                "isBanned": user.is_banned,
                "createdAt": user.created_at
            }
            for user in users
        ]
    }


@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Fetch detailed information about a specific user, including device history.
    
    Args:
        user_id (int): The ID of the user to fetch.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: A success flag and detailed user information with device list.
        
    Raises:
        HTTPException: 404 if the user is not found.
    """
    # 1. Fetch the user
    user = db.query(User).filter(
        User.id == user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 2. Fetch all devices for this user
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == user.id
    ).all()
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "phoneNumber": user.phone_number,
            "role": user.role,
            "authProvider": user.auth_provider,
            "isEmailVerified": user.is_email_verified,
            "isBanned": user.is_banned,
            "createdAt": user.created_at,
            "devices": [
                {
                    "id": device.id,
                    "deviceId": device.device_id,
                    "createdAt": device.created_at,
                    "lastLoginAt": device.last_login_at
                }
                for device in devices
            ]
        }
    }


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Ban a user account, preventing them from logging in.
    
    Args:
        user_id (int): The ID of the user to ban.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message confirming the ban.
        
    Raises:
        HTTPException: 404 if the user is not found.
        HTTPException: 400 if the admin tries to ban themselves.
    """
    # 1. Fetch the user
    user = db.query(User).filter(
        User.id == user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 2. Prevent admins from banning themselves
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot ban yourself"
        )
    
    # 3. Set ban flag and commit
    user.is_banned = True
    db.commit()
    
    return {
        "success": True,
        "message": "User banned successfully"
    }


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Unban a user account, restoring their access.
    
    Args:
        user_id (int): The ID of the user to unban.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message confirming the unban.
        
    Raises:
        HTTPException: 404 if the user is not found.
    """
    # 1. Fetch the user
    user = db.query(User).filter(
        User.id == user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 2. Clear ban flag and commit
    user.is_banned = False
    db.commit()
    
    return {
        "success": True,
        "message": "User unbanned successfully"
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Permanently delete a user account and all associated devices.
    
    Warning: This is a hard delete. The user and all their device records
    will be removed from the database entirely.
    
    Args:
        user_id (int): The ID of the user to delete.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message confirming deletion.
        
    Raises:
        HTTPException: 404 if the user is not found.
        HTTPException: 400 if the admin tries to delete themselves.
    """
    # 1. Fetch the user
    user = db.query(User).filter(
        User.id == user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 2. Prevent admins from deleting themselves
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete yourself"
        )
    
    # 3. Delete all associated devices first (cleanup)
    db.query(UserDevice).filter(
        UserDevice.user_id == user.id
    ).delete()
    
    # 4. Delete the user and commit
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "message": "User deleted successfully"
    }


@router.delete("/users/{user_id}/devices/{device_id}")
def remove_user_device(
    user_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Remove a specific device from a user's account.
    
    This forces the user to re-authenticate on that device on their next login.
    
    Args:
        user_id (int): The ID of the user who owns the device.
        device_id (int): The ID of the device to remove.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message confirming device removal.
        
    Raises:
        HTTPException: 404 if the device is not found or doesn't belong to the user.
    """
    # 1. Fetch the device, ensuring it belongs to the specified user
    device = db.query(UserDevice).filter(
        UserDevice.id == device_id,
        UserDevice.user_id == user_id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )
    
    # 2. Delete the device and commit
    db.delete(device)
    db.commit()
    
    return {
        "success": True,
        "message": "Device removed successfully"
    }