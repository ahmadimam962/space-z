"""
Purchases Module
----------------
This module handles all purchase-related operations including:
- Creating purchase requests for paid courses
- Auto-enrollment for free courses
- Admin purchase request management (list, approve, reject)
- Notifications for purchase status changes

The module supports both user-facing and admin-facing endpoints.
"""

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local application imports
from app.database import get_db
from app.models import (
    PurchaseRequest,
    Course,
    User,
    Enrollment,
    Notification,
    AuditLog
)
from app.schemas import PurchaseCourseRequest, PurchaseAdminNoteRequest
from app.users import get_current_user
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================

router = APIRouter(tags=["Purchases"])


# ==========================================
# Helper Functions
# ==========================================

def purchase_to_admin_dict(purchase: PurchaseRequest, db: Session) -> Dict[str, Any]:
    """
    Convert a PurchaseRequest object to a dictionary format for admin display.
    
    This function fetches related user and course data to provide a complete
    view of the purchase request for the admin dashboard.
    
    Args:
        purchase (PurchaseRequest): The purchase request object to convert.
        db (Session): The database session for querying related data.
        
    Returns:
        dict: A dictionary containing purchase details with nested user and course info.
    """
    # Fetch related user data
    user = db.query(User).filter(User.id == purchase.user_id).first()
    
    # Fetch related course data
    course = db.query(Course).filter(Course.id == purchase.course_id).first()
    
    return {
        "id": purchase.id,
        "status": purchase.status,
        "transferNumber": purchase.transfer_number,
        "adminNote": purchase.admin_note,
        "createdAt": purchase.created_at,
        "student": {
            "id": user.id if user else None,
            "name": f"{user.first_name} {user.last_name}" if user else "-",
            "email": user.email if user else "-",
            "phoneNumber": user.phone_number if user else "-"
        },
        "course": {
            "id": course.id if course else None,
            "title": course.title if course else "-",
            "price": course.price if course else 0
        }
    }


# ==========================================
# User Endpoints
# ==========================================

@router.post("/api/purchases")
def create_purchase_request(
    request: PurchaseCourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new purchase request for a course.
    
    Flow:
    1. Validate the course exists and is active
    2. If the course is free, auto-enroll the user immediately
    3. If the course is paid, check for existing pending requests
    4. Validate the transfer number hasn't been used before
    5. Check if the user already owns the course
    6. Create the purchase request with "pending" status
    
    Args:
        request (PurchaseCourseRequest): The purchase request data (course_id, transfer_number).
        db (Session): The database session.
        current_user (User): The authenticated user making the request.
        
    Returns:
        dict: Success message and enrollment details.
        
    Raises:
        HTTPException: 404 if course not found or not active.
        HTTPException: 400 if pending request exists, transfer number used, or already enrolled.
    """
    # 1. Validate course exists and is active
    course = db.query(Course).filter(
        Course.id == request.course_id,
        Course.status == "active"
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course.id,
        Enrollment.status == "active"
    ).first()

    if existing_enrollment:
        raise HTTPException(
            status_code=400,
            detail="You already own this course"
        )

    
    # 2. Handle free courses - auto-enroll immediately
    if not course.is_paid or course.price == 0:
        # Create enrollment
        enrollment = Enrollment(
            user_id=current_user.id,
            course_id=course.id,
            status="active"
        )
        
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            title="تم تفعيل الكورس المجاني",
            message=f"تمت إضافة كورس {course.title} إلى حسابك."
        )
        
        # Save to database
        db.add(enrollment)
        db.add(notification)
        db.commit()
        
        return {
            "success": True,
            "message": "Free course enrolled successfully",
            "freeCourse": True
        }
    
    # 3. Check for existing pending purchase request
    existing = db.query(PurchaseRequest).filter(
        PurchaseRequest.user_id == current_user.id,
        PurchaseRequest.course_id == course.id,
        PurchaseRequest.status == "pending"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending request"
        )
    
    # 4. Validate transfer number hasn't been used
    existing_transfer = db.query(PurchaseRequest).filter(
        PurchaseRequest.transfer_number == request.transfer_number,
        PurchaseRequest.status.in_(["pending", "approved"])
    ).first()
    
    if existing_transfer:
        raise HTTPException(
            status_code=400,
            detail="Transfer number already used"
        )
    
    # 5. Create the purchase request
    purchase = PurchaseRequest(
        user_id=current_user.id,
        course_id=course.id,
        transfer_number=request.transfer_number,
        status="pending"
    )
    
    db.add(purchase)
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase request submitted successfully"
    }


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/purchase-requests")
def admin_list_purchase_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    List all purchase requests for admin review.
    
    Args:
        status (Optional[str]): Filter by status ("pending", "approved", "rejected").
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: List of purchase requests with full details.
    """
    # Build query with optional status filter
    query = db.query(PurchaseRequest)
    
    if status:
        query = query.filter(PurchaseRequest.status == status)
    
    # Fetch all matching requests, ordered by creation date (newest first)
    purchases = query.order_by(PurchaseRequest.created_at.desc()).all()
    
    return {
        "success": True,
        "data": [
            purchase_to_admin_dict(purchase, db)
            for purchase in purchases
        ]
    }


@router.post("/api/admin/purchase-requests/{purchase_id}/approve")
def approve_purchase_request(
    purchase_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Approve a pending purchase request and enroll the user.
    
    Flow:
    1. Validate the purchase request exists
    2. Ensure the request is in "pending" status
    3. Update status to "approved"
    4. Create enrollment if it doesn't exist
    5. Send notification to the user
    
    Args:
        purchase_id (int): The ID of the purchase request to approve.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException: 404 if purchase request not found.
        HTTPException: 400 if request is not in "pending" status.
    """
    # 1. Fetch the purchase request
    purchase = db.query(PurchaseRequest).filter(
        PurchaseRequest.id == purchase_id
    ).first()
    
    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase request not found"
        )
    
    # 2. Validate status is "pending"
    if purchase.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Purchase request is not pending"
        )
    
    # 3. Update status to "approved"
    purchase.status = "approved"
    
    # 4. Create enrollment if it doesn't exist
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == purchase.user_id,
        Enrollment.course_id == purchase.course_id
    ).first()
    
    if not existing_enrollment:
        enrollment = Enrollment(
            user_id=purchase.user_id,
            course_id=purchase.course_id,
            status="active"
        )
        db.add(enrollment)
    
    # 5. Create notification
    notification = Notification(
        user_id=purchase.user_id,
        title="تم قبول طلب الشراء",
        message="تم قبول طلبك وتم تفعيل الكورس على حسابك."
    )

    audit = AuditLog(
        admin_id=admin.id,
        action="approve_purchase",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Approved purchase request {purchase.id}"
    )


    db.add(audit)
    db.add(notification)
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase request approved successfully"
    }


@router.post("/api/admin/purchase-requests/{purchase_id}/reject")
def reject_purchase_request(
    purchase_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Reject a pending purchase request.
    
    Flow:
    1. Validate the purchase request exists
    2. Ensure the request is in "pending" status
    3. Update status to "rejected"
    4. Send notification to the user
    
    Args:
        purchase_id (int): The ID of the purchase request to reject.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException: 404 if purchase request not found.
        HTTPException: 400 if request is not in "pending" status.
    """
    # 1. Fetch the purchase request
    purchase = db.query(PurchaseRequest).filter(
        PurchaseRequest.id == purchase_id
    ).first()
    
    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase request not found"
        )
    
    # 2. Validate status is "pending"
    if purchase.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Purchase request is not pending"
        )
    
    # 3. Update status to "rejected"
    purchase.status = "rejected"
    
    # 4. Create notification
    notification = Notification(
        user_id=purchase.user_id,
        title="تم رفض طلب الشراء",
        message="تم رفض طلبك. يرجى التأكد من رقم التحويلة أو التواصل مع الدعم."
    )

    audit = AuditLog(
        admin_id=admin.id,
        action="reject_purchase",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Rejected purchase request {purchase.id}"
    )


    db.add(audit)
    
    db.add(notification)
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase request rejected successfully"
    }



@router.get("/api/my-purchases")
def my_purchase_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    purchases = db.query(PurchaseRequest).filter(
        PurchaseRequest.user_id == current_user.id
    ).order_by(
        PurchaseRequest.created_at.desc()
    ).all()

    result = []

    for purchase in purchases:
        course = db.query(Course).filter(
            Course.id == purchase.course_id
        ).first()

        result.append({
            "id": purchase.id,
            "status": purchase.status,
            "transferNumber": purchase.transfer_number,
            "adminNote": purchase.admin_note,
            "createdAt": purchase.created_at,
            "course": {
                "id": course.id if course else None,
                "title": course.title if course else "-",
                "price": course.price if course else 0
            }
        })

    return {
        "success": True,
        "data": result
    }


@router.put("/api/admin/purchase-requests/{purchase_id}/note")
def update_purchase_admin_note(
    purchase_id: int,
    request: PurchaseAdminNoteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    purchase = db.query(PurchaseRequest).filter(
        PurchaseRequest.id == purchase_id
    ).first()

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase request not found"
        )

    purchase.admin_note = request.admin_note

    audit = AuditLog(
        admin_id=admin.id,
        action="update_purchase_note",
        target_type="purchase_request",
        target_id=purchase.id,
        details=f"Updated note for purchase request {purchase.id}"
    )

    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Admin note updated successfully"
    }


@router.get("/api/admin/users/{user_id}/purchases")
def admin_user_purchase_history(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    purchases = db.query(PurchaseRequest).filter(
        PurchaseRequest.user_id == user_id
    ).order_by(
        PurchaseRequest.created_at.desc()
    ).all()

    result = []

    for purchase in purchases:
        course = db.query(Course).filter(
            Course.id == purchase.course_id
        ).first()

        result.append({
            "id": purchase.id,
            "status": purchase.status,
            "transferNumber": purchase.transfer_number,
            "adminNote": purchase.admin_note,
            "createdAt": purchase.created_at,
            "course": {
                "id": course.id if course else None,
                "title": course.title if course else "-",
                "price": course.price if course else 0
            }
        })

    return {
        "success": True,
        "data": result
    }