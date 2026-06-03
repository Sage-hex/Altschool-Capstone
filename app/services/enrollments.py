from __future__ import annotations

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Enrollment, User
from app.repositories import courses as course_repo
from app.repositories import enrollments as enrollment_repo
from app.services.courses import get_admin_course
from app.services.errors import api_error


def enroll_student(db: Session, *, student: User, course_id: int) -> Enrollment:
    course = get_admin_course(db, course_id)
    if not course.is_active:
        raise api_error(status.HTTP_409_CONFLICT, "COURSE_INACTIVE", "Enrollment fails because the course is inactive.")
    if course_repo.active_enrollment_count(db, course_id) >= course.capacity:
        raise api_error(status.HTTP_409_CONFLICT, "COURSE_FULL", "Course has reached maximum enrollment capacity.")
    try:
        enrollment = enrollment_repo.create_enrollment(db, user_id=student.id, course_id=course_id)
    except IntegrityError as error:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "ALREADY_ENROLLED", "Student is already enrolled in this course.") from error
    full_enrollment = enrollment_repo.get_enrollment_by_id(db, enrollment.id)
    if full_enrollment is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
    return full_enrollment


def deregister_student(db: Session, *, student: User, course_id: int) -> None:
    get_admin_course(db, course_id)
    enrollment = enrollment_repo.get_enrollment(db, user_id=student.id, course_id=course_id)
    if enrollment is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
    enrollment_repo.delete_enrollment(db, enrollment)


def list_student_enrollments(db: Session, *, student: User) -> list[Enrollment]:
    return enrollment_repo.list_user_enrollments(db, student.id)


def list_all_enrollments(db: Session) -> list[Enrollment]:
    return enrollment_repo.list_enrollments(db)


def list_enrollments_for_course(db: Session, *, course_id: int) -> list[Enrollment]:
    get_admin_course(db, course_id)
    return enrollment_repo.list_course_enrollments(db, course_id)


def remove_student_from_course(db: Session, *, course_id: int, user_id: int) -> None:
    get_admin_course(db, course_id)
    enrollment = enrollment_repo.get_enrollment(db, user_id=user_id, course_id=course_id)
    if enrollment is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
    enrollment_repo.delete_enrollment(db, enrollment)
