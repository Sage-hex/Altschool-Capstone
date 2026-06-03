from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Course, Enrollment


def list_active_courses(db: Session) -> list[Course]:
    return list(db.scalars(select(Course).where(Course.is_active.is_(True)).order_by(Course.created_at.desc())).all())


def get_course_by_id(db: Session, course_id: int) -> Course | None:
    return db.get(Course, course_id)


def get_active_course_by_id(db: Session, course_id: int) -> Course | None:
    return db.scalar(select(Course).where(Course.id == course_id, Course.is_active.is_(True)))


def get_course_by_code(db: Session, code: str) -> Course | None:
    return db.scalar(select(Course).where(func.lower(Course.code) == code.lower()))


def create_course(db: Session, *, title: str, code: str, capacity: int, created_by: int) -> Course:
    course = Course(title=title, code=code.upper(), capacity=capacity, created_by=created_by, is_active=True)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course: Course, *, title: str, code: str, capacity: int) -> Course:
    course.title = title
    course.code = code.upper()
    course.capacity = capacity
    db.commit()
    db.refresh(course)
    return course


def set_course_active(db: Session, course: Course, is_active: bool) -> Course:
    course.is_active = is_active
    db.commit()
    db.refresh(course)
    return course


def active_enrollment_count(db: Session, course_id: int) -> int:
    return db.scalar(select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)) or 0
