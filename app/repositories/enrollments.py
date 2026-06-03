from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Enrollment


def get_enrollment(db: Session, *, user_id: int, course_id: int) -> Enrollment | None:
    return db.scalar(select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id))


def get_enrollment_by_id(db: Session, enrollment_id: int) -> Enrollment | None:
    return db.scalar(select(Enrollment).options(joinedload(Enrollment.user), joinedload(Enrollment.course)).where(Enrollment.id == enrollment_id))


def create_enrollment(db: Session, *, user_id: int, course_id: int) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def delete_enrollment(db: Session, enrollment: Enrollment) -> None:
    db.delete(enrollment)
    db.commit()


def list_enrollments(db: Session) -> list[Enrollment]:
    return list(db.scalars(select(Enrollment).options(joinedload(Enrollment.user), joinedload(Enrollment.course)).order_by(Enrollment.created_at.desc())).all())


def list_user_enrollments(db: Session, user_id: int) -> list[Enrollment]:
    return list(
        db.scalars(
            select(Enrollment)
            .options(joinedload(Enrollment.user), joinedload(Enrollment.course))
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.created_at.desc())
        ).all()
    )


def list_course_enrollments(db: Session, course_id: int) -> list[Enrollment]:
    return list(
        db.scalars(
            select(Enrollment)
            .options(joinedload(Enrollment.user), joinedload(Enrollment.course))
            .where(Enrollment.course_id == course_id)
            .order_by(Enrollment.created_at.desc())
        ).all()
    )
