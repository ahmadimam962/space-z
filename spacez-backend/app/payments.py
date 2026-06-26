"""
Payment Settings Module
-----------------------
This module handles all payment settings operations including:
- Public listing of active payment methods (for users)
- Admin CRUD operations for payment settings (Create, Read, Update, Delete)

Payment settings represent the available payment methods users can use
to purchase courses (e.g., Bank Transfer, PayPal, etc.).
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local application imports
from app.database import get_db
from app.models import PaymentSetting, User
from app.schemas import (
    PaymentSettingCreateRequest,
    PaymentSettingUpdateRequest
)
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================

router = APIRouter(tags=["Payment Settings"])


# ==========================================
# Helper Functions
# ==========================================

def payment_to_dict(payment: PaymentSetting) -> Dict[str, Any]:
    """
    Convert a PaymentSetting SQLAlchemy object to a dictionary for API responses.
    
    Maps snake_case database fields to camelCase for frontend compatibility.
    
    Args:
        payment (PaymentSetting): The payment setting object to convert.
        
    Returns:
        dict: A dictionary containing the payment setting details.
    """
    return {
        "id": payment.id,
        "methodName": payment.method_name,
        "accountName": payment.account_name,
        "accountNumber": payment.account_number,
        "instructions": payment.instructions,
        "isActive": payment.is_active,
        "createdAt": payment.created_at
    }


# ==========================================
# Public Endpoints (No Auth Required)
# ==========================================

@router.get("/api/payment-settings")
def list_public_payment_settings(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all active payment settings for public use.
    
    This endpoint is accessible without authentication and only returns
    payment methods that are currently active.
    
    Args:
        db (Session): The database session.
        
    Returns:
        dict: A list of active payment settings.
    """
    # Fetch only active payment settings, ordered by creation date (newest first)
    payments = db.query(PaymentSetting).filter(
        PaymentSetting.is_active.is_(True)
    ).order_by(
        PaymentSetting.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [
            payment_to_dict(payment)
            for payment in payments
        ]
    }


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/payment-settings")
def admin_list_payment_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    List all payment settings for admin review (includes inactive ones).
    
    Args:
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: A list of all payment settings (active and inactive).
    """
    # Fetch ALL payment settings regardless of status
    payments = db.query(PaymentSetting).order_by(
        PaymentSetting.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [
            payment_to_dict(payment)
            for payment in payments
        ]
    }


@router.post("/api/admin/payment-settings")
def create_payment_setting(
    request: PaymentSettingCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Create a new payment setting.
    
    Args:
        request (PaymentSettingCreateRequest): The payment setting data.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message and the created payment setting data.
    """
    # Create new PaymentSetting instance from request data
    payment = PaymentSetting(
        method_name=request.method_name,
        account_name=request.account_name,
        account_number=request.account_number,
        instructions=request.instructions,
        is_active=request.is_active
    )

    # Save to database
    db.add(payment)
    db.commit()

    # Refresh to get auto-generated fields (id, created_at)
    db.refresh(payment)

    return {
        "success": True,
        "message": "Payment setting created successfully",
        "data": payment_to_dict(payment)
    }


@router.put("/api/admin/payment-settings/{payment_id}")
def update_payment_setting(
    payment_id: int,
    request: PaymentSettingUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Update an existing payment setting (partial update supported).
    
    Only fields that are not None in the request will be updated.
    
    Args:
        payment_id (int): The ID of the payment setting to update.
        request (PaymentSettingUpdateRequest): The fields to update.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message and the updated payment setting data.
        
    Raises:
        HTTPException: 404 if payment setting not found.
    """
    # Fetch the payment setting
    payment = db.query(PaymentSetting).filter(
        PaymentSetting.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment setting not found"
        )

    # Update only the fields that were provided (not None)
    if request.method_name is not None:
        payment.method_name = request.method_name

    if request.account_name is not None:
        payment.account_name = request.account_name

    if request.account_number is not None:
        payment.account_number = request.account_number

    if request.instructions is not None:
        payment.instructions = request.instructions

    if request.is_active is not None:
        payment.is_active = request.is_active

    # Commit changes to database
    db.commit()
    db.refresh(payment)

    return {
        "success": True,
        "message": "Payment setting updated successfully",
        "data": payment_to_dict(payment)
    }


@router.delete("/api/admin/payment-settings/{payment_id}")
def delete_payment_setting(
    payment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Delete a payment setting permanently.
    
    Args:
        payment_id (int): The ID of the payment setting to delete.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException: 404 if payment setting not found.
    """
    # Fetch the payment setting
    payment = db.query(PaymentSetting).filter(
        PaymentSetting.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment setting not found"
        )

    # Delete and commit
    db.delete(payment)
    db.commit()

    return {
        "success": True,
        "message": "Payment setting deleted successfully"
    }