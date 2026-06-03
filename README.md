# Course Enrollment Platform API

A FastAPI-based REST API for a course enrollment platform. It implements the capstone requirements: authentication, role-based authorization, course management, student enrollment, admin oversight, persistent relational storage, validation, error handling, and automated tests.

## Tech stack

- **FastAPI** for the HTTP API, OpenAPI documentation, dependency injection, and request validation.
- **Pydantic** for typed request and response schemas.
- **SQLite** via Python's standard `sqlite3` module for relational persistence.
- **Python standard cryptography primitives** (`hashlib.scrypt`, `hmac`) for password hashing and signed bearer tokens.
- **Pytest** and FastAPI `TestClient` for API-level tests.

## Features

- User registration, login, and authenticated profile lookup.
- JWT-style bearer tokens signed with HMAC SHA-256.
- Passwords hashed with `scrypt` and unique per-user salts.
- Role-based authorization for `student` and `admin` users.
- Public course listing and course detail endpoints.
- Admin-only course creation, updates, and deletion.
- Student-only course enrollment and enrollment cancellation.
- Admin enrollment reporting and platform statistics.
- SQLite relational database with foreign keys, uniqueness constraints, and capacity checks.
- Consistent JSON API errors for application errors and FastAPI validation for request errors.

## Requirements

- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000` by default. FastAPI's generated documentation is available at `/docs` and `/redoc`.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `./course-enrollment.sqlite` | SQLite database path. Use `:memory:` for ephemeral tests. |
| `JWT_SECRET` | development fallback | Secret used to sign bearer tokens. Set this in production. |

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
