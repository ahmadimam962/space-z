"""
Enrollments Module
هذا الموديول مسؤول عن إدارة تسجيلات المستخدمين في الكورسات:
- عرض الكورسات التي يملكها المستخدم
- منح كورس لمستخدم معين (عملية إدارية)
- تسجيل العمليات في AuditLog وإرسال الإشعارات
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Enrollment, Course, User, Notification, AuditLog, CourseLesson, LessonProgress
from app.users import get_current_user
from app.schemas import GrantCourseRequest
from app.admin import get_current_admin


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(tags=["Enrollments"])


# ==========================================
# Helper Functions
# ==========================================
def my_course_to_dict(enrollment: Enrollment, course: Course, db: Session, user_id: int) -> Dict[str, Any]:
    """تحويل Enrollment + Course إلى قاموس مع نسبة التقدم."""

    total_lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course.id
    ).count()

    completed_lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == user_id,
        LessonProgress.course_id == course.id,
        LessonProgress.is_completed == True
    ).count()

    progress_percent = round((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    return {
        "enrollmentId": enrollment.id,
        "enrolledAt": enrollment.enrolled_at,
        "status": enrollment.status,
        "progress": progress_percent,
        "progressPercent": progress_percent,
        "totalLessons": total_lessons,
        "completedLessons": completed_lessons,
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "price": course.price,
            "thumbnailUrl": course.thumbnail_url,
            "isPaid": course.is_paid
        }
    }


# ==========================================
# User Endpoints
# ==========================================

@router.get("/api/my-courses")
def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """سرد الكورسات التي يملكها المستخدم الحالي."""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status == "active"
    ).order_by(Enrollment.enrolled_at.desc()).all()

    result = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            result.append(my_course_to_dict(enrollment, course, db, current_user.id))

    return {"success": True, "data": result}


# ==========================================
# Admin Endpoints
# ==========================================

@router.post("/api/admin/enrollments/grant")
def grant_course_to_user(
    request: GrantCourseRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """منح كورس لمستخدم معين (عملية إدارية)."""
    # 1. التحقق من وجود المستخدم والكورس
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    course = db.query(Course).filter(Course.id == request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. التحقق من عدم وجود تسجيل مسبق
    existing = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == course.id,
        Enrollment.status == "active"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already has this course"
        )

    # 3. إنشاء التسجيل + إشعار + سجل تدقيق
    enrollment = Enrollment(
        user_id=user.id,
        course_id=course.id,
        status="active"
    )

    notification = Notification(
        user_id=user.id,
        title="تمت إضافة كورس إلى حسابك",
        message=f"قام الأدمن بإضافة كورس {course.title} إلى حسابك."
    )

    audit = AuditLog(
        admin_id=admin.id,
        action="grant_course",
        target_type="enrollment",
        target_id=user.id,
        details=f"Granted course {course.id} - {course.title} to user {user.id} - {user.email}"
    )

    db.add(enrollment)
    db.add(notification)
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Course granted successfully"
    }