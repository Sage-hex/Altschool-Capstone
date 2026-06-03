# Course Enrollment Platform API

A FastAPI-based REST API for a course enrollment platform. It implements the capstone requirements: authentication, role-based authorization, course management, student enrollment, admin oversight, **real PostgreSQL persistence**, validation, error handling, and automated tests.

## Tech stack

- **FastAPI** for the HTTP API, OpenAPI documentation, dependency injection, and request validation.
- **Pydantic** for typed request and response schemas.
- **PostgreSQL** as the production database.
- **SQLAlchemy 2.x** for ORM models, database sessions, constraints, and portable test configuration.
- **psycopg 3** as the PostgreSQL driver.
- **Python standard cryptography primitives** (`hashlib.scrypt`, `hmac`) for password hashing and signed bearer tokens.
- **Pytest** and FastAPI `TestClient` for API-level tests.

## Features

- User registration, login, and authenticated profile lookup.
- JWT-style bearer tokens signed with HMAC SHA-256.
- Default generated 64-character JWT secret in `.env.example`; replace it with a new secret before production deployment.
- Passwords hashed with `scrypt` and unique per-user salts.
- Role-based authorization for `student` and `admin` users.
- Public course listing and course detail endpoints.
- Admin-only course creation, updates, and deletion.
- Student-only course enrollment and enrollment cancellation.
- Admin enrollment reporting and platform statistics.
- Relational database constraints for roles, statuses, positive course capacity, unique emails, and duplicate enrollment prevention.
- Consistent JSON API errors for application errors and FastAPI validation for request errors.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Create the PostgreSQL database locally:

```bash
createdb course_enrollment
```

If your PostgreSQL user, password, host, or database name differs, update `DATABASE_URL` in `.env`.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000` by default. FastAPI's generated documentation is available at `/docs` and `/redoc`.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/course_enrollment` | SQLAlchemy PostgreSQL connection URL. |
| `JWT_SECRET` | generated 64-character development secret | Secret used to sign bearer tokens. Generate a new value for production. |

Generate a new 64-character JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## API overview

### Authentication and users

- `POST /api/auth/register` registers a user. Body: `name`, `email`, `password`, optional `role` (`student` or `admin`).
- `POST /api/auth/login` returns a bearer token for valid credentials.
- `GET /api/users/me` returns the authenticated user's public profile.

### Courses

- `GET /api/courses` lists all courses with enrollment counts and available seats.
- `GET /api/courses/{course_id}` returns one course.
- `POST /api/courses` creates a course. Admin only.
- `PUT /api/courses/{course_id}` updates a course. Admin only.
- `DELETE /api/courses/{course_id}` deletes a course. Admin only.

### Enrollments

- `POST /api/courses/{course_id}/enroll` enrolls the authenticated student.
- `DELETE /api/courses/{course_id}/enroll` cancels the authenticated student's enrollment.
- `GET /api/enrollments/me` lists the authenticated student's enrollments.
- `GET /api/admin/enrollments` lists all enrollments. Admin only.
- `GET /api/admin/stats` returns user, course, enrollment, and popular-course statistics. Admin only.

## Test

```bash
pytest
```

Tests use a temporary file-backed SQLite database through SQLAlchemy so the suite can run without requiring a local PostgreSQL service. The application default and deployment configuration remain PostgreSQL.
