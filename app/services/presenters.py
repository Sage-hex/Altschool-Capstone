from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Course, Enrollment
from app.repositories.courses import active_enrollment_count


def course_to_response(db: Session, course: Course) -> dict[str, object]:
    enrollment_count = active_enrollment_count(db, course.id)
    return {
        "id": course.id,
        "title": course.title,
        "code": course.code,
        "capacity": course.capacity,
        "is_active": course.is_active,
        "available_seats": course.capacity - enrollment_count,
        "enrollment_count": enrollment_count,
        "created_by": course.created_by,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
    }


def enrollment_to_response(enrollment: Enrollment) -> dict[str, object]:
    return {
        "id": enrollment.id,
        "created_at": enrollment.created_at,
        "user_id": enrollment.user_id,
        "user_name": enrollment.user.name,
        "user_email": enrollment.user.email,
        "course_id": enrollment.course_id,
        "course_title": enrollment.course.title,
        "course_code": enrollment.course.code,
    }
