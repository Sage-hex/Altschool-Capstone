from __future__ import annotations

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Course
from app.repositories import courses as course_repo
from app.services.errors import api_error


def list_public_courses(db: Session) -> list[Course]:
    return course_repo.list_active_courses(db)


def get_public_course(db: Session, course_id: int) -> Course:
    course = course_repo.get_active_course_by_id(db, course_id)
    if course is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "COURSE_NOT_FOUND", "Active course not found.")
    return course


def get_admin_course(db: Session, course_id: int) -> Course:
    course = course_repo.get_course_by_id(db, course_id)
    if course is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "COURSE_NOT_FOUND", "Course not found.")
    return course


def create_admin_course(db: Session, *, title: str, code: str, capacity: int, created_by: int) -> Course:
    try:
        return course_repo.create_course(db, title=title.strip(), code=code.upper(), capacity=capacity, created_by=created_by)
    except IntegrityError as error:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "COURSE_CODE_ALREADY_EXISTS", "A course with this code already exists.") from error


def update_admin_course(db: Session, course_id: int, *, title: str, code: str, capacity: int) -> Course:
    course = get_admin_course(db, course_id)
    active_count = course_repo.active_enrollment_count(db, course_id)
    if capacity < active_count:
        raise api_error(status.HTTP_409_CONFLICT, "CAPACITY_BELOW_ENROLLMENT_COUNT", "Course capacity cannot be lower than current enrollments.")
    try:
        return course_repo.update_course(db, course, title=title.strip(), code=code.upper(), capacity=capacity)
    except IntegrityError as error:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "COURSE_CODE_ALREADY_EXISTS", "A course with this code already exists.") from error


def activate_course(db: Session, course_id: int) -> Course:
    return course_repo.set_course_active(db, get_admin_course(db, course_id), True)


def deactivate_course(db: Session, course_id: int) -> Course:
    return course_repo.set_course_active(db, get_admin_course(db, course_id), False)
