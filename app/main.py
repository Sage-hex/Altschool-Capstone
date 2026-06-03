from __future__ import annotations

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import Course, Enrollment, User, create_session_factory, get_session, init_database
from app.schemas import CourseCreate, CourseOut, EnrollmentOut, TokenResponse, UserCreate, UserLogin, UserOut
from app.security import create_access_token, decode_access_token, hash_password, verify_password

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/course_enrollment"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
JWT_SECRET = os.getenv("JWT_SECRET", "e809b8e03532bdbdd6ba0eda42bbdf0dd0f0638696013253cdb322957be301a8")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_app(database_url: str | None = None, jwt_secret: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Course Enrollment Platform API",
        version="1.0.0",
        description="FastAPI REST API for course management, authentication, enrollment, and admin reporting backed by PostgreSQL.",
    )
    session_factory, engine = create_session_factory(database_url or DATABASE_URL)
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.state.jwt_secret = jwt_secret or JWT_SECRET

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed.", "details": exc.errors()}},
        )

    def db_session() -> Generator[Session, None, None]:
        yield from get_session(app.state.session_factory)

    def current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(db_session)]) -> User:
        payload = decode_access_token(token, app.state.jwt_secret)
        if not payload or "sub" not in payload:
            raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
        user = db.get(User, int(payload["sub"]))
        if user is None:
            raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
        return user

    def require_role(role: str):
        def dependency(user: Annotated[User, Depends(current_user)]) -> User:
            if user.role != role:
                raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", f"Only {role}s can perform this action.")
            return user

        return dependency

    @app.on_event("startup")
    def initialize_database() -> None:
        init_database(app.state.engine)

    @app.on_event("shutdown")
    def close_database() -> None:
        app.state.engine.dispose()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    def register(payload: UserCreate, db: Annotated[Session, Depends(db_session)]) -> dict[str, object]:
        user = User(
            name=payload.name.strip(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise api_error(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_REGISTERED", "A user with this email already exists.") from error
        db.refresh(user)
        return {"user": user, "token": create_access_token({"sub": user.id, "role": user.role}, app.state.jwt_secret)}

    @app.post("/api/auth/login", response_model=TokenResponse)
    def login(payload: UserLogin, db: Annotated[Session, Depends(db_session)]) -> dict[str, object]:
        user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email or password is incorrect.")
        return {"user": user, "token": create_access_token({"sub": user.id, "role": user.role}, app.state.jwt_secret)}

    @app.get("/api/users/me", response_model=dict[str, UserOut])
    def me(user: Annotated[User, Depends(current_user)]) -> dict[str, User]:
        return {"user": user}

    @app.get("/api/courses", response_model=dict[str, list[CourseOut]])
    def list_courses(db: Annotated[Session, Depends(db_session)]) -> dict[str, list[dict[str, object]]]:
        courses = db.scalars(select(Course).order_by(Course.created_at.desc())).all()
        return {"courses": [course_to_response(db, course) for course in courses]}

    @app.get("/api/courses/{course_id}", response_model=dict[str, CourseOut])
    def get_course(course_id: int, db: Annotated[Session, Depends(db_session)]) -> dict[str, dict[str, object]]:
        return {"course": course_to_response(db, find_course(db, course_id))}

    @app.post("/api/courses", response_model=dict[str, CourseOut], status_code=status.HTTP_201_CREATED)
    def create_course(
        payload: CourseCreate,
        admin: Annotated[User, Depends(require_role("admin"))],
        db: Annotated[Session, Depends(db_session)],
    ) -> dict[str, dict[str, object]]:
        course = Course(
            title=payload.title.strip(),
            description=payload.description.strip(),
            instructor=payload.instructor.strip(),
            capacity=payload.capacity,
            created_by=admin.id,
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return {"course": course_to_response(db, course)}

    @app.put("/api/courses/{course_id}", response_model=dict[str, CourseOut])
    def update_course(
        course_id: int,
        payload: CourseCreate,
        admin: Annotated[User, Depends(require_role("admin"))],
        db: Annotated[Session, Depends(db_session)],
    ) -> dict[str, dict[str, object]]:
        course = find_course(db, course_id)
        active_enrollments = active_enrollment_count(db, course_id)
        if payload.capacity < active_enrollments:
            raise api_error(status.HTTP_409_CONFLICT, "CAPACITY_BELOW_ENROLLMENT_COUNT", "Course capacity cannot be lower than current active enrollments.")
        course.title = payload.title.strip()
        course.description = payload.description.strip()
        course.instructor = payload.instructor.strip()
        course.capacity = payload.capacity
        db.commit()
        db.refresh(course)
        return {"course": course_to_response(db, course)}

    @app.delete("/api/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_course(
        course_id: int,
        admin: Annotated[User, Depends(require_role("admin"))],
        db: Annotated[Session, Depends(db_session)],
    ) -> Response:
        course = find_course(db, course_id)
        db.delete(course)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/courses/{course_id}/enroll", response_model=dict[str, EnrollmentOut], status_code=status.HTTP_201_CREATED)
    def enroll(course_id: int, student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(db_session)]) -> dict[str, dict[str, object]]:
        course = find_course(db, course_id)
        if course.capacity - active_enrollment_count(db, course_id) <= 0:
            raise api_error(status.HTTP_409_CONFLICT, "COURSE_FULL", "Course has reached maximum enrollment capacity.")
        enrollment = Enrollment(user_id=student.id, course_id=course_id)
        db.add(enrollment)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise api_error(status.HTTP_409_CONFLICT, "ALREADY_ENROLLED", "Student is already enrolled in this course.") from error
        db.refresh(enrollment)
        return {"enrollment": enrollment_to_response(db, enrollment.id)}

    @app.delete("/api/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
    def cancel_enrollment(course_id: int, student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(db_session)]) -> Response:
        find_course(db, course_id)
        enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == student.id, Enrollment.course_id == course_id))
        if enrollment is None:
            raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
        db.delete(enrollment)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/enrollments/me", response_model=dict[str, list[EnrollmentOut]])
    def my_enrollments(student: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(db_session)]) -> dict[str, list[dict[str, object]]]:
        enrollments = db.scalars(
            select(Enrollment)
            .options(joinedload(Enrollment.user), joinedload(Enrollment.course))
            .where(Enrollment.user_id == student.id)
            .order_by(Enrollment.enrolled_at.desc())
        ).all()
        return {"enrollments": [enrollment_to_dict(enrollment) for enrollment in enrollments]}

    @app.get("/api/admin/enrollments", response_model=dict[str, list[EnrollmentOut]])
    def all_enrollments(admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(db_session)]) -> dict[str, list[dict[str, object]]]:
        enrollments = db.scalars(select(Enrollment).options(joinedload(Enrollment.user), joinedload(Enrollment.course)).order_by(Enrollment.enrolled_at.desc())).all()
        return {"enrollments": [enrollment_to_dict(enrollment) for enrollment in enrollments]}

    @app.get("/api/admin/stats")
    def admin_stats(admin: Annotated[User, Depends(require_role("admin"))], db: Annotated[Session, Depends(db_session)]) -> dict[str, object]:
        users_total = db.scalar(select(func.count(User.id))) or 0
        students_total = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
        admins_total = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
        courses = db.scalars(select(Course)).all()
        popular_courses = sorted((course_to_response(db, course) for course in courses), key=lambda item: (-int(item["enrollment_count"]), str(item["title"])))[:5]
        return {
            "stats": {
                "users": {"total": users_total, "students": students_total, "admins": admins_total},
                "courses": {"total": len(courses)},
                "enrollments": {"active": db.scalar(select(func.count(Enrollment.id)).where(Enrollment.status == "active")) or 0},
                "popular_courses": popular_courses,
            }
        }

    return app


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def find_course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "COURSE_NOT_FOUND", "Course not found.")
    return course


def active_enrollment_count(db: Session, course_id: int) -> int:
    return db.scalar(select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id, Enrollment.status == "active")) or 0


def course_to_response(db: Session, course: Course) -> dict[str, object]:
    enrollment_count = active_enrollment_count(db, course.id)
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "instructor": course.instructor,
        "capacity": course.capacity,
        "available_seats": course.capacity - enrollment_count,
        "enrollment_count": enrollment_count,
        "created_by": course.created_by,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
    }


def enrollment_to_response(db: Session, enrollment_id: int) -> dict[str, object]:
    enrollment = db.scalar(select(Enrollment).options(joinedload(Enrollment.user), joinedload(Enrollment.course)).where(Enrollment.id == enrollment_id))
    if enrollment is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
    return enrollment_to_dict(enrollment)


def enrollment_to_dict(enrollment: Enrollment) -> dict[str, object]:
    return {
        "id": enrollment.id,
        "status": enrollment.status,
        "enrolled_at": enrollment.enrolled_at,
        "updated_at": enrollment.updated_at,
        "user_id": enrollment.user_id,
        "user_name": enrollment.user.name,
        "user_email": enrollment.user.email,
        "course_id": enrollment.course_id,
        "course_title": enrollment.course.title,
        "course_instructor": enrollment.course.instructor,
    }


app = create_app()
