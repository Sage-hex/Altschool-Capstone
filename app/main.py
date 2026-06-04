from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import create_session_factory, init_database
from app.routers import admin, auth, courses, enrollments

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/course_enrollment"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
JWT_SECRET = os.getenv("JWT_SECRET", "e809b8e03532bdbdd6ba0eda42bbdf0dd0f0638696013253cdb322957be301a8")


def create_app(database_url: str | None = None, jwt_secret: str | None = None, create_tables: bool = False) -> FastAPI:
    app = FastAPI(
        title="Course Enrollment Platform API",
        version="1.0.0",
        description="FastAPI REST API for course management, authentication, enrollment, and admin reporting backed by PostgreSQL.",
    )
    session_factory, engine = create_session_factory(database_url or DATABASE_URL)
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.state.jwt_secret = jwt_secret or JWT_SECRET
    app.state.create_tables = create_tables

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

    @app.on_event("startup")
    def initialize_database_for_tests() -> None:
        if app.state.create_tables:
            init_database(app.state.engine)

    @app.on_event("shutdown")
    def close_database() -> None:
        app.state.engine.dispose()

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(courses.router)
    app.include_router(enrollments.router)
    app.include_router(admin.router)
    return app


app = create_app()
