from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import Course, Enrollment, User
from app.schemas import EnrollmentOut
from app.services import enrollments as enrollment_service
from app.services.presenters import course_to_response, enrollment_to_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/enrollments", response_model=dict[str, list[EnrollmentOut]])
def all_enrollments(admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict[str, object]]]:
    return {"enrollments": [enrollment_to_response(enrollment) for enrollment in enrollment_service.list_all_enrollments(db)]}


@router.get("/courses/{course_id}/enrollments", response_model=dict[str, list[EnrollmentOut]])
def course_enrollments(course_id: int, admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict[str, object]]]:
    return {"enrollments": [enrollment_to_response(enrollment) for enrollment in enrollment_service.list_enrollments_for_course(db, course_id=course_id)]}


@router.delete("/courses/{course_id}/enrollments/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_from_course(
    course_id: int,
    user_id: int,
    admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    enrollment_service.remove_student_from_course(db, course_id=course_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/stats")
def admin_stats(admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    users_total = db.scalar(select(func.count(User.id))) or 0
    students_total = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
    admins_total = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
    courses = db.scalars(select(Course)).all()
    active_enrollments = db.scalar(select(func.count(Enrollment.id))) or 0
    popular_courses = sorted((course_to_response(db, course) for course in courses), key=lambda item: (-int(item["enrollment_count"]), str(item["title"])))[:5]
    return {
        "stats": {
            "users": {"total": users_total, "students": students_total, "admins": admins_total},
            "courses": {"total": len(courses), "active": sum(1 for course in courses if course.is_active)},
            "enrollments": {"active": active_enrollments},
            "popular_courses": popular_courses,
        }
    }
