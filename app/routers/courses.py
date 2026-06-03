from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User
from app.schemas import CourseCreate, CourseOut, CourseUpdate
from app.services import courses as course_service
from app.services.presenters import course_to_response

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=dict[str, list[CourseOut]])
def list_courses(db: Annotated[Session, Depends(get_db)]) -> dict[str, list[dict[str, object]]]:
    return {"courses": [course_to_response(db, course) for course in course_service.list_public_courses(db)]}


@router.get("/{course_id}", response_model=dict[str, CourseOut])
def get_course(course_id: int, db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, object]]:
    return {"course": course_to_response(db, course_service.get_public_course(db, course_id))}


@router.post("", response_model=dict[str, CourseOut], status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, dict[str, object]]:
    course = course_service.create_admin_course(db, title=payload.title, code=payload.code, capacity=payload.capacity, created_by=admin.id)
    return {"course": course_to_response(db, course)}


@router.put("/{course_id}", response_model=dict[str, CourseOut])
def update_course(
    course_id: int,
    payload: CourseUpdate,
    admin: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, dict[str, object]]:
    course = course_service.update_admin_course(db, course_id, title=payload.title, code=payload.code, capacity=payload.capacity)
    return {"course": course_to_response(db, course)}


@router.patch("/{course_id}/activate", response_model=dict[str, CourseOut])
def activate_course(course_id: int, admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, object]]:
    return {"course": course_to_response(db, course_service.activate_course(db, course_id))}


@router.patch("/{course_id}/deactivate", response_model=dict[str, CourseOut])
def deactivate_course(course_id: int, admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, object]]:
    return {"course": course_to_response(db, course_service.deactivate_course(db, course_id))}


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(get_db)]) -> Response:
    course_service.deactivate_course(db, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
