"""
Progress Module
هذا الموديول مسؤول عن إدارة وتتبع تقدم المستخدم في الدروس والكورسات:
- وضع علامة "مكتمل" على الدروس
- حساب نسبة التقدم في الكورسات الفردية
- استعراض ملخص تقدم المستخدم في جميع الكورسات المسجل بها
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local imports
from app.database import get_db
from app.models import User, Course, CourseLesson, Enrollment, LessonProgress
from app.schemas import MarkLessonProgressRequest
from app.users import get_current_user


# ==========================================
# Router Initialization
# ==========================================
router = APIRouter(tags=["Progress"])


# ==========================================
# Helper Functions
# ==========================================

def ensure_enrolled(user_id: int, course_id: int, db: Session):
    """التحقق من أن المستخدم مسجل في الكورس قبل السماح بأي إجراء."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user_id,
        Enrollment.course_id == course_id,
        Enrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this course"
        )
    return enrollment


# ==========================================
# Endpoints
# ==========================================

@router.post("/api/progress/lesson")
def mark_lesson_progress(
    request: MarkLessonProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """تحديث حالة تقدم درس معين (مكتمل / غير مكتمل)."""
    # 1. التحقق من وجود الدرس
    lesson = db.query(CourseLesson).filter(CourseLesson.id == request.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # 2. التحقق من صلاحية الوصول
    ensure_enrolled(current_user.id, lesson.course_id, db)

    # 3. جلب أو إنشاء سجل التقدم
    progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.lesson_id == lesson.id
    ).first()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            course_id=lesson.course_id,
            lesson_id=lesson.id
        )
        db.add(progress)

    # 4. تحديث البيانات
    progress.is_completed = request.is_completed
    progress.last_watched_at = datetime.utcnow()
    progress.completed_at = datetime.utcnow() if request.is_completed else None

    db.commit()
    db.refresh(progress)

    return {
        "success": True,
        "message": "Lesson progress updated successfully",
        "data": {
            "lessonId": progress.lesson_id,
            "courseId": progress.course_id,
            "isCompleted": progress.is_completed,
            "completedAt": progress.completed_at,
            "lastWatchedAt": progress.last_watched_at
        }
    }


@router.get("/api/courses/{course_id}/progress")
def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """استرجاع نسبة تقدم المستخدم في كورس محدد."""
    # 1. التحقق من وجود الكورس والتسجيل
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    ensure_enrolled(current_user.id, course_id, db)

    # 2. حساب التقدم
    total_lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id
    ).count()

    completed_lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.course_id == course_id,
        LessonProgress.is_completed == True
    ).count()

    last_progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.course_id == course_id
    ).order_by(LessonProgress.last_watched_at.desc()).first()

    percent = round((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    return {
        "success": True,
        "data": {
            "courseId": course_id,
            "totalLessons": total_lessons,
            "completedLessons": completed_lessons,
            "progressPercent": percent,
            "lastLessonId": last_progress.lesson_id if last_progress else None,
            "lastWatchedAt": last_progress.last_watched_at if last_progress else None
        }
    }


@router.get("/api/my-progress")
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """استرجاع ملخص تقدم المستخدم في جميع الكورسات التي يشترك بها."""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status == "active"
    ).all()

    result = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if not course:
            continue

        total_lessons = db.query(CourseLesson).filter(
            CourseLesson.course_id == course.id
        ).count()

        completed_lessons = db.query(LessonProgress).filter(
            LessonProgress.user_id == current_user.id,
            LessonProgress.course_id == course.id,
            LessonProgress.is_completed == True
        ).count()

        last_progress = db.query(LessonProgress).filter(
            LessonProgress.user_id == current_user.id,
            LessonProgress.course_id == course.id
        ).order_by(LessonProgress.last_watched_at.desc()).first()

        percent = round((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

        result.append({
            "courseId": course.id,
            "courseTitle": course.title,
            "totalLessons": total_lessons,
            "completedLessons": completed_lessons,
            "progressPercent": percent,
            "lastLessonId": last_progress.lesson_id if last_progress else None,
            "lastWatchedAt": last_progress.last_watched_at if last_progress else None
        })

    return {"success": True, "data": result}