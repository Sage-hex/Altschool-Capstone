from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User
from app.schemas import EnrollmentOut
from app.services import enrollments as enrollment_service
from app.services.presenters import enrollment_to_response

router = APIRouter(prefix="/api", tags=["enrollments"])


@router.post("/courses/{course_id}/enroll", response_model=dict[str, EnrollmentOut], status_code=status.HTTP_201_CREATED)
def enroll(course_id: int, student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, object]]:
    return {"enrollment": enrollment_to_response(enrollment_service.enroll_student(db, student=student, course_id=course_id))}


@router.delete("/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
def deregister(course_id: int, student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]) -> Response:
    enrollment_service.deregister_student(db, student=student, course_id=course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/enrollments/me", response_model=dict[str, list[EnrollmentOut]])
def my_enrollments(student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict[str, object]]]:
    return {"enrollments": [enrollment_to_response(enrollment) for enrollment in enrollment_service.list_student_enrollments(db, student=student)]}
