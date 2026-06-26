from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    Course,
    CourseSection,
    CourseLesson,
    Enrollment
)
from app.schemas import (
    SectionCreateRequest,
    SectionUpdateRequest,
    LessonCreateRequest,
    LessonUpdateRequest
)
from app.admin import get_current_admin
from app.users import get_current_user


router = APIRouter(tags=["Course Content"])


def lesson_to_dict(lesson: CourseLesson):
    return {
        "id": lesson.id,
        "courseId": lesson.course_id,
        "sectionId": lesson.section_id,
        "title": lesson.title,
        "description": lesson.description,
        "lessonType": lesson.lesson_type,
        "videoProvider": lesson.video_provider,
        "sortOrder": lesson.sort_order,
        "isFreePreview": lesson.is_free_preview,
        "createdAt": lesson.created_at
    }


def section_to_dict(section: CourseSection, db: Session, include_lessons=True):
    data = {
        "id": section.id,
        "courseId": section.course_id,
        "title": section.title,
        "sortOrder": section.sort_order,
        "createdAt": section.created_at
    }

    if include_lessons:
        lessons = db.query(CourseLesson).filter(
            CourseLesson.section_id == section.id
        ).order_by(
            CourseLesson.sort_order.asc(),
            CourseLesson.id.asc()
        ).all()

        data["lessons"] = [
            lesson_to_dict(lesson)
            for lesson in lessons
        ]

    return data


def ensure_course_exists(course_id: int, db: Session):
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    return course


def ensure_student_has_course(course_id: int, user_id: int, db: Session):
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user_id,
        Enrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this course"
        )

    return enrollment


@router.get("/api/admin/courses/{course_id}/sections")
def admin_list_sections(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    ensure_course_exists(course_id, db)

    sections = db.query(CourseSection).filter(
        CourseSection.course_id == course_id
    ).order_by(
        CourseSection.sort_order.asc(),
        CourseSection.id.asc()
    ).all()

    return {
        "success": True,
        "data": [
            section_to_dict(section, db)
            for section in sections
        ]
    }


@router.post("/api/admin/courses/{course_id}/sections")
def admin_create_section(
    course_id: int,
    request: SectionCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    ensure_course_exists(course_id, db)

    section = CourseSection(
        course_id=course_id,
        title=request.title,
        sort_order=request.sort_order
    )

    db.add(section)
    db.commit()
    db.refresh(section)

    return {
        "success": True,
        "message": "Section created successfully",
        "data": section_to_dict(section, db)
    }


@router.put("/api/admin/sections/{section_id}")
def admin_update_section(
    section_id: int,
    request: SectionUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id
    ).first()

    if not section:
        raise HTTPException(
            status_code=404,
            detail="Section not found"
        )

    if request.title is not None:
        section.title = request.title

    if request.sort_order is not None:
        section.sort_order = request.sort_order

    db.commit()
    db.refresh(section)

    return {
        "success": True,
        "message": "Section updated successfully",
        "data": section_to_dict(section, db)
    }


@router.delete("/api/admin/sections/{section_id}")
def admin_delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id
    ).first()

    if not section:
        raise HTTPException(
            status_code=404,
            detail="Section not found"
        )

    db.query(CourseLesson).filter(
        CourseLesson.section_id == section.id
    ).delete()

    db.delete(section)
    db.commit()

    return {
        "success": True,
        "message": "Section deleted successfully"
    }


@router.post("/api/admin/sections/{section_id}/lessons")
def admin_create_lesson(
    section_id: int,
    request: LessonCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id
    ).first()

    if not section:
        raise HTTPException(
            status_code=404,
            detail="Section not found"
        )

    if request.lesson_type not in ["video", "pdf", "text"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid lesson type"
        )

    lesson = CourseLesson(
        course_id=section.course_id,
        section_id=section.id,
        title=request.title,
        description=request.description,
        lesson_type=request.lesson_type,
        video_provider=request.video_provider,
        video_url=request.video_url,
        pdf_url=request.pdf_url,
        content_text=request.content_text,
        sort_order=request.sort_order,
        is_free_preview=request.is_free_preview
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return {
        "success": True,
        "message": "Lesson created successfully",
        "data": lesson_to_dict(lesson)
    }


@router.put("/api/admin/lessons/{lesson_id}")
def admin_update_lesson(
    lesson_id: int,
    request: LessonUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    if request.lesson_type is not None:
        if request.lesson_type not in ["video", "pdf", "text"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid lesson type"
            )
        lesson.lesson_type = request.lesson_type

    if request.title is not None:
        lesson.title = request.title

    if request.description is not None:
        lesson.description = request.description

    if request.video_provider is not None:
        lesson.video_provider = request.video_provider

    if request.video_url is not None:
        lesson.video_url = request.video_url

    if request.pdf_url is not None:
        lesson.pdf_url = request.pdf_url

    if request.content_text is not None:
        lesson.content_text = request.content_text

    if request.sort_order is not None:
        lesson.sort_order = request.sort_order

    if request.is_free_preview is not None:
        lesson.is_free_preview = request.is_free_preview

    db.commit()
    db.refresh(lesson)

    return {
        "success": True,
        "message": "Lesson updated successfully",
        "data": lesson_to_dict(lesson)
    }


@router.delete("/api/admin/lessons/{lesson_id}")
def admin_delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    db.delete(lesson)
    db.commit()

    return {
        "success": True,
        "message": "Lesson deleted successfully"
    }


@router.get("/api/courses/{course_id}/content")
def student_course_content(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = ensure_course_exists(course_id, db)

    ensure_student_has_course(
        course_id,
        current_user.id,
        db
    )

    sections = db.query(CourseSection).filter(
        CourseSection.course_id == course_id
    ).order_by(
        CourseSection.sort_order.asc(),
        CourseSection.id.asc()
    ).all()

    return {
        "success": True,
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "thumbnailUrl": course.thumbnail_url
        },
        "sections": [
            section_to_dict(section, db)
            for section in sections
        ]
    }


@router.get("/api/lessons/{lesson_id}/watch")
def watch_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    ensure_student_has_course(
        lesson.course_id,
        current_user.id,
        db
    )

    return {
        "success": True,
        "lesson": {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "lessonType": lesson.lesson_type,
            "videoProvider": lesson.video_provider,
            "videoUrl": lesson.video_url,
            "pdfUrl": lesson.pdf_url,
            "contentText": lesson.content_text
        }
    }