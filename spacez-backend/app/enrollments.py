from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Enrollment, Course, User, Notification, AuditLog
from app.users import get_current_user
from app.schemas import GrantCourseRequest
from app.admin import get_current_admin

router = APIRouter(
    tags=["Enrollments"]
)


def my_course_to_dict(enrollment: Enrollment, course: Course):
    return {
        "enrollmentId": enrollment.id,
        "enrolledAt": enrollment.enrolled_at,
        "status": enrollment.status,
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "price": course.price,
            "thumbnailUrl": course.thumbnail_url,
            "isPaid": course.is_paid
        }
    }


@router.get("/api/my-courses")
def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status == "active"
    ).order_by(
        Enrollment.enrolled_at.desc()
    ).all()

    result = []

    for enrollment in enrollments:
        course = db.query(Course).filter(
            Course.id == enrollment.course_id
        ).first()

        if course:
            result.append(
                my_course_to_dict(enrollment, course)
            )

    return {
        "success": True,
        "data": result
    }

@router.post("/api/admin/enrollments/grant")
def grant_course_to_user(
    request: GrantCourseRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    course = db.query(Course).filter(Course.id == request.course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

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