"""
Courses Module
This module handles all course-related operations including:

Public Endpoints:
- List all active courses (public catalog)
- Get single course details (public)
- List featured courses

Student Endpoints:
- List store courses (courses the user hasn't enrolled in yet)

Admin Endpoints:
- List all courses (including hidden/draft)
- Create new courses
- Update existing courses (partial updates supported)
- Delete courses

The module supports both public-facing and admin-facing endpoints.
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local application imports
from app.database import get_db
from app.models import Course, User, Enrollment
from app.schemas import CourseCreateRequest, CourseUpdateRequest
from app.admin import get_current_admin
from app.users import get_current_user
from app.audit_utils import create_audit_log


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(tags=["Courses"])


# ==========================================
# Helper Functions
# ==========================================

def course_to_dict(course: Course) -> Dict[str, Any]:
    """
    Convert a Course object to a dictionary format for API responses.
    This helper ensures consistent field naming (camelCase) for the frontend
    and handles all course attributes.

    Args:
        course (Course): The course ORM object to convert.

    Returns:
        dict: A dictionary with camelCase keys suitable for JSON serialization.
    """
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "price": course.price,
        "thumbnailUrl": course.thumbnail_url,
        "status": course.status,
        "isPaid": course.is_paid,
        "createdAt": course.created_at,
        "isFeatured": course.is_featured
    }


# ==========================================
# Public Endpoints
# ==========================================

@router.get("/api/courses")
def list_public_courses(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Fetch all active courses for public display.
    This endpoint is used by unauthenticated users to browse the course catalog.
    Only courses with status="active" are returned, ordered by newest first.
    """
    courses = db.query(Course).filter(
        Course.status == "active"
    ).order_by(
        Course.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [course_to_dict(course) for course in courses]
    }


@router.get("/api/courses/{course_id}")
def get_public_course(
    course_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Fetch a single course's details for public display.
    Only active courses can be viewed publicly. Hidden or draft courses
    will return 404 to unauthenticated users.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == "active"
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return {
        "success": True,
        "data": course_to_dict(course)
    }


@router.get("/api/featured-courses")
def list_featured_courses(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Fetch all active featured courses for public display."""
    courses = db.query(Course).filter(
        Course.status == "active",
        Course.is_featured == True
    ).order_by(
        Course.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [course_to_dict(course) for course in courses]
    }


# ==========================================
# Student Endpoints
# ==========================================

@router.get("/api/store/courses")
def list_store_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Fetch courses available for purchase (excluding already enrolled courses).
    This endpoint shows the "store" view for authenticated students,
    displaying only courses they haven't enrolled in yet.
    """
    # 1. Fetch all course IDs the user is already enrolled in
    enrolled_course_ids = db.query(Enrollment.course_id).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status == "active"
    ).all()
    enrolled_course_ids = [item[0] for item in enrolled_course_ids]

    # 2. Query active courses
    query = db.query(Course).filter(Course.status == "active")

    # 3. Exclude already enrolled courses (if any)
    if enrolled_course_ids:
        query = query.filter(Course.id.notin_(enrolled_course_ids))

    # 4. Order by newest first
    courses = query.order_by(
        Course.is_featured.desc(),
        Course.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [course_to_dict(course) for course in courses]
    }


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/courses")
def admin_list_courses(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    offset = (page - 1) * limit

    query = db.query(Course)

    total = query.count()

    courses = query.order_by(
        Course.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "data": [course_to_dict(course) for course in courses]
    }


@router.post("/api/admin/courses")
def create_course(
    request: CourseCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Create a new course."""
    # 1. Validate course status
    if request.status not in ["active", "hidden"]:
        raise HTTPException(status_code=400, detail="Invalid course status")

    # 2. Validate price is not negative
    if request.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")

    # 3. Create the course
    course = Course(
        title=request.title,
        description=request.description,
        price=request.price,
        thumbnail_url=request.thumbnail_url,
        status=request.status,
        is_paid=request.is_paid,
        is_featured=request.is_featured
    )

    # 4. Save to database
    db.add(course)
    db.commit()
    db.refresh(course)
    
    
    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="create_course",
        target_type="course",
        target_id=course.id,
        details=f"Created course {course.id} - {course.title}"
    )
    db.commit()

    return {
        "success": True,
        "message": "Course created successfully",
        "data": course_to_dict(course)
    }


@router.put("/api/admin/courses/{course_id}")
def update_course(
    course_id: int,
    request: CourseUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Update an existing course (supports partial updates).
    Only fields provided in the request (not None) will be updated.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Update status (with validation)
    if request.status is not None:
        if request.status not in ["active", "hidden"]:
            raise HTTPException(status_code=400, detail="Invalid course status")
        course.status = request.status

    # Update price (with validation)
    if request.price is not None:
        if request.price < 0:
            raise HTTPException(status_code=400, detail="Price cannot be negative")
        course.price = request.price

    # Update other fields if provided
    if request.title is not None:
        course.title = request.title

    if request.description is not None:
        course.description = request.description

    if request.thumbnail_url is not None:
        course.thumbnail_url = request.thumbnail_url

    if request.is_paid is not None:
        course.is_paid = request.is_paid

    if request.is_featured is not None:
        course.is_featured = request.is_featured


    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="update_course",
        target_type="course",
        target_id=course.id,
        details=f"Updated course {course.id} - {course.title}"
    )

    db.commit()
    db.refresh(course)

    return {
        "success": True,
        "message": "Course updated successfully",
        "data": course_to_dict(course)
    }


@router.delete("/api/admin/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Delete a course permanently.
    Warning: This is a hard delete. Consider using update(status="hidden")
    for soft deletion if historical data needs to be preserved.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    create_audit_log(
        db=db,
        admin_id=admin.id,
        action="delete_course",
        target_type="course",
        target_id=course.id,
        details=f"Deleted course {course.id} - {course.title}"
    )

    db.delete(course)
    db.commit()

    return {
        "success": True,
        "message": "Course deleted successfully"
    }