"""
Courses Module
--------------
This module handles all course-related operations including:

1. Public Endpoints:
   - List all active courses (public catalog)
   - Get single course details (public)

2. Student Endpoints:
   - List store courses (courses the user hasn't enrolled in yet)

3. Admin Endpoints:
   - List all courses (including hidden/draft)
   - Create new courses
   - Update existing courses (partial updates supported)
   - Delete courses

The module supports both public-facing and admin-facing endpoints.
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local application imports
from app.database import get_db
from app.models import Course, User, Enrollment
from app.schemas import CourseCreateRequest, CourseUpdateRequest
from app.admin import get_current_admin
from app.users import get_current_user


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
    
    Args:
        db (Session): The database session (injected via dependency).
        
    Returns:
        dict: A success flag and a list of active courses.
    """
    # Query only active courses, ordered by creation date (newest first)
    courses = db.query(Course).filter(
        Course.status == "active"
    ).order_by(
        Course.created_at.desc()
    ).all()
    
    return {
        "success": True,
        "data": [
            course_to_dict(course)
            for course in courses
        ]
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
    
    Args:
        course_id (int): The ID of the course to fetch.
        db (Session): The database session.
        
    Returns:
        dict: A success flag and the course details.
        
    Raises:
        HTTPException: 404 if the course is not found or not active.
    """
    # Fetch the course, ensuring it's active
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == "active"
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    
    return {
        "success": True,
        "data": course_to_dict(course)
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
    
    Args:
        db (Session): The database session.
        current_user (User): The authenticated student user.
        
    Returns:
        dict: A success flag and a list of available courses.
    """
    # 1. Fetch all course IDs the user is already enrolled in
    enrolled_course_ids = db.query(Enrollment.course_id).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status == "active"
    ).all()
    
    # Extract course IDs from the result (list of tuples)
    enrolled_course_ids = [item[0] for item in enrolled_course_ids]
    
    # 2. Query active courses
    query = db.query(Course).filter(
        Course.status == "active"
    )
    
    # 3. Exclude already enrolled courses (if any)
    if enrolled_course_ids:
        query = query.filter(
            Course.id.notin_(enrolled_course_ids)
        )
    
    # 4. Order by newest first
    courses = query.order_by(
        Course.created_at.desc()
    ).all()
    
    return {
        "success": True,
        "data": [
            course_to_dict(course)
            for course in courses
        ]
    }


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/api/admin/courses")
def admin_list_courses(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Fetch all courses for the admin dashboard.
    
    Unlike the public endpoint, this returns ALL courses regardless of status,
    so admins can manage hidden and draft courses as well.
    
    Args:
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: A success flag and a list of all courses.
    """
    # Fetch all courses (active, hidden, draft), ordered by newest first
    courses = db.query(Course).order_by(
        Course.created_at.desc()
    ).all()
    
    return {
        "success": True,
        "data": [
            course_to_dict(course)
            for course in courses
        ]
    }


@router.post("/api/admin/courses")
def create_course(
    request: CourseCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Create a new course.
    
    Args:
        request (CourseCreateRequest): The course data.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message and the newly created course data.
        
    Raises:
        HTTPException: 400 if status is invalid or price is negative.
    """
    # 1. Validate course status
    if request.status not in ["active", "hidden"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid course status"
        )
    
    # 2. Validate price is not negative
    if request.price < 0:
        raise HTTPException(
            status_code=400,
            detail="Price cannot be negative"
        )
    
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
    
    Only fields provided in the request (not None) will be updated,
    allowing admins to modify specific fields without affecting others.
    
    Args:
        course_id (int): The ID of the course to update.
        request (CourseUpdateRequest): The partial update data.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message and the updated course data.
        
    Raises:
        HTTPException: 404 if the course is not found.
        HTTPException: 400 if status is invalid or price is negative.
    """
    # 1. Fetch the existing course
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    
    # 2. Apply partial updates - validate and update each field if provided
    
    # Update status (with validation)
    if request.status is not None:
        if request.status not in ["active", "hidden"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid course status"
            )
        course.status = request.status
    
    # Update price (with validation)
    if request.price is not None:
        if request.price < 0:
            raise HTTPException(
                status_code=400,
                detail="Price cannot be negative"
            )
        course.price = request.price
    
    # Update title
    if request.title is not None:
        course.title = request.title
    
    # Update description
    if request.description is not None:
        course.description = request.description
    
    # Update thumbnail URL
    if request.thumbnail_url is not None:
        course.thumbnail_url = request.thumbnail_url
    
    # Update is_paid flag
    if request.is_paid is not None:
        course.is_paid = request.is_paid
        
    if request.is_featured is not None:
        course.is_featured = request.is_featured
    
    # 3. Commit changes and refresh to get updated timestamps
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
    
    Warning: This is a hard delete. The course will be removed from the database
    entirely. Consider using update(status="hidden") for soft deletion if
    historical data needs to be preserved.
    
    Args:
        course_id (int): The ID of the course to delete.
        db (Session): The database session.
        admin (User): The authenticated admin user.
        
    Returns:
        dict: Success message confirming deletion.
        
    Raises:
        HTTPException: 404 if the course is not found.
    """
    # 1. Fetch the course to delete
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    
    # 2. Delete the record and commit
    db.delete(course)
    db.commit()
    
    return {
        "success": True,
        "message": "Course deleted successfully"
    }

@router.get("/api/featured-courses")
def list_featured_courses(
    db: Session = Depends(get_db)
):
    courses = db.query(Course).filter(
        Course.status == "active",
        Course.is_featured == True
    ).order_by(
        Course.created_at.desc()
    ).all()

    return {
        "success": True,
        "data": [
            course_to_dict(course)
            for course in courses
        ]
    }