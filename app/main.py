from __future__ import annotations

import os
import sqlite3
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer
from app.database import COURSE_SELECT, ENROLLMENT_SELECT, connect, database_path_from_url
from app.schemas import CourseCreate, CourseOut, EnrollmentOut, TokenResponse, UserCreate, UserLogin, UserOut
from app.security import create_access_token, decode_access_token, hash_password, verify_password

DATABASE_URL = os.getenv("DATABASE_URL", "./course-enrollment.sqlite")
JWT_SECRET = os.getenv("JWT_SECRET", "replace-this-secret-in-production")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_app(database_url: str | None = None, jwt_secret: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Course Enrollment Platform API",
        version="1.0.0",
        description="FastAPI REST API for course management, authentication, enrollment, and admin reporting.",
    )
    app.state.db = connect(database_path_from_url(database_url or DATABASE_URL))
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

    def db() -> sqlite3.Connection:
        return app.state.db

    def current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> sqlite3.Row:
        payload = decode_access_token(token, app.state.jwt_secret)
        if not payload or "sub" not in payload:
            raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
        user = db().execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()
        if user is None:
            raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
        return user

    def require_role(role: str):
        def dependency(user: Annotated[sqlite3.Row, Depends(current_user)]) -> sqlite3.Row:
            if user["role"] != role:
                raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", f"Only {role}s can perform this action.")
            return user

        return dependency

    @app.on_event("shutdown")
    def close_database() -> None:
        app.state.db.close()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    def register(payload: UserCreate) -> dict[str, object]:
        try:
            cursor = db().execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (payload.name.strip(), payload.email.lower(), hash_password(payload.password), payload.role),
            )
            db().commit()
        except sqlite3.IntegrityError as error:
            if "UNIQUE" in str(error):
                raise api_error(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_REGISTERED", "A user with this email already exists.") from error
            raise
        user = db().execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return {"user": row_to_dict(user), "token": create_access_token({"sub": user["id"], "role": user["role"]}, app.state.jwt_secret)}

    @app.post("/api/auth/login", response_model=TokenResponse)
    def login(payload: UserLogin) -> dict[str, object]:
        user = db().execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (payload.email,)).fetchone()
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email or password is incorrect.")
        return {"user": row_to_dict(user), "token": create_access_token({"sub": user["id"], "role": user["role"]}, app.state.jwt_secret)}

    @app.get("/api/users/me", response_model=dict[str, UserOut])
    def me(user: Annotated[sqlite3.Row, Depends(current_user)]) -> dict[str, dict[str, object]]:
        return {"user": row_to_dict(user)}

    @app.get("/api/courses", response_model=dict[str, list[CourseOut]])
    def list_courses() -> dict[str, list[dict[str, object]]]:
        courses = db().execute(f"{COURSE_SELECT} GROUP BY c.id ORDER BY c.created_at DESC").fetchall()
        return {"courses": [row_to_dict(course) for course in courses]}

    @app.get("/api/courses/{course_id}", response_model=dict[str, CourseOut])
    def get_course(course_id: int) -> dict[str, dict[str, object]]:
        return {"course": row_to_dict(find_course(db(), course_id))}

    @app.post("/api/courses", response_model=dict[str, CourseOut], status_code=status.HTTP_201_CREATED)
    def create_course(payload: CourseCreate, admin: Annotated[sqlite3.Row, Depends(require_role("admin"))]) -> dict[str, dict[str, object]]:
        cursor = db().execute(
            "INSERT INTO courses (title, description, instructor, capacity, created_by) VALUES (?, ?, ?, ?, ?)",
            (payload.title.strip(), payload.description.strip(), payload.instructor.strip(), payload.capacity, admin["id"]),
        )
        db().commit()
        return {"course": row_to_dict(find_course(db(), cursor.lastrowid))}

    @app.put("/api/courses/{course_id}", response_model=dict[str, CourseOut])
    def update_course(course_id: int, payload: CourseCreate, admin: Annotated[sqlite3.Row, Depends(require_role("admin"))]) -> dict[str, dict[str, object]]:
        find_course(db(), course_id)
        active_enrollments = db().execute("SELECT COUNT(*) AS total FROM enrollments WHERE course_id = ? AND status = 'active'", (course_id,)).fetchone()["total"]
        if payload.capacity < active_enrollments:
            raise api_error(status.HTTP_409_CONFLICT, "CAPACITY_BELOW_ENROLLMENT_COUNT", "Course capacity cannot be lower than current active enrollments.")
        db().execute(
            """
            UPDATE courses
            SET title = ?, description = ?, instructor = ?, capacity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payload.title.strip(), payload.description.strip(), payload.instructor.strip(), payload.capacity, course_id),
        )
        db().commit()
        return {"course": row_to_dict(find_course(db(), course_id))}

    @app.delete("/api/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_course(course_id: int, admin: Annotated[sqlite3.Row, Depends(require_role("admin"))]) -> Response:
        find_course(db(), course_id)
        db().execute("DELETE FROM courses WHERE id = ?", (course_id,))
        db().commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/courses/{course_id}/enroll", response_model=dict[str, EnrollmentOut], status_code=status.HTTP_201_CREATED)
    def enroll(course_id: int, student: Annotated[sqlite3.Row, Depends(require_role("student"))]) -> dict[str, dict[str, object]]:
        course = find_course(db(), course_id)
        if course["available_seats"] <= 0:
            raise api_error(status.HTTP_409_CONFLICT, "COURSE_FULL", "Course has reached maximum enrollment capacity.")
        try:
            cursor = db().execute("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", (student["id"], course_id))
            db().commit()
        except sqlite3.IntegrityError as error:
            if "UNIQUE" in str(error):
                raise api_error(status.HTTP_409_CONFLICT, "ALREADY_ENROLLED", "Student is already enrolled in this course.") from error
            raise
        return {"enrollment": row_to_dict(find_enrollment(db(), cursor.lastrowid))}

    @app.delete("/api/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
    def cancel_enrollment(course_id: int, student: Annotated[sqlite3.Row, Depends(require_role("student"))]) -> Response:
        find_course(db(), course_id)
        result = db().execute("DELETE FROM enrollments WHERE user_id = ? AND course_id = ?", (student["id"], course_id))
        db().commit()
        if result.rowcount == 0:
            raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/enrollments/me", response_model=dict[str, list[EnrollmentOut]])
    def my_enrollments(student: Annotated[sqlite3.Row, Depends(require_role("student"))]) -> dict[str, list[dict[str, object]]]:
        enrollments = db().execute(f"{ENROLLMENT_SELECT} WHERE e.user_id = ? ORDER BY e.enrolled_at DESC", (student["id"],)).fetchall()
        return {"enrollments": [row_to_dict(enrollment) for enrollment in enrollments]}

    @app.get("/api/admin/enrollments", response_model=dict[str, list[EnrollmentOut]])
    def all_enrollments(admin: Annotated[sqlite3.Row, Depends(require_role("admin"))]) -> dict[str, list[dict[str, object]]]:
        enrollments = db().execute(f"{ENROLLMENT_SELECT} ORDER BY e.enrolled_at DESC").fetchall()
        return {"enrollments": [row_to_dict(enrollment) for enrollment in enrollments]}

    @app.get("/api/admin/stats")
    def admin_stats(admin: Annotated[sqlite3.Row, Depends(require_role("admin"))]) -> dict[str, object]:
        users = db().execute("SELECT COUNT(*) AS total, SUM(role = 'student') AS students, SUM(role = 'admin') AS admins FROM users").fetchone()
        courses = db().execute("SELECT COUNT(*) AS total FROM courses").fetchone()
        enrollments = db().execute("SELECT COUNT(*) AS total FROM enrollments WHERE status = 'active'").fetchone()
        popular_courses = db().execute(f"{COURSE_SELECT} GROUP BY c.id ORDER BY enrollment_count DESC, c.title ASC LIMIT 5").fetchall()
        return {
            "stats": {
                "users": {"total": users["total"] or 0, "students": users["students"] or 0, "admins": users["admins"] or 0},
                "courses": {"total": courses["total"] or 0},
                "enrollments": {"active": enrollments["total"] or 0},
                "popular_courses": [row_to_dict(course) for course in popular_courses],
            }
        }

    return app


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return dict(row)


def find_course(connection: sqlite3.Connection, course_id: int) -> sqlite3.Row:
    course = connection.execute(f"{COURSE_SELECT} WHERE c.id = ? GROUP BY c.id", (course_id,)).fetchone()
    if course is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "COURSE_NOT_FOUND", "Course not found.")
    return course


def find_enrollment(connection: sqlite3.Connection, enrollment_id: int) -> sqlite3.Row:
    enrollment = connection.execute(f"{ENROLLMENT_SELECT} WHERE e.id = ?", (enrollment_id,)).fetchone()
    if enrollment is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "ENROLLMENT_NOT_FOUND", "Enrollment not found.")
    return enrollment


app = create_app()
