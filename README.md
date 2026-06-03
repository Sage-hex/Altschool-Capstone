# Course Enrollment Platform API

A FastAPI-based REST API for a course enrollment platform. It implements the capstone requirements: authentication, role-based authorization, course management, student enrollment, administrative oversight, **real PostgreSQL persistence**, Alembic migrations, validation, error handling, automated API tests, and cloud deployment configuration.

## Tech stack

- **FastAPI** for the HTTP API, OpenAPI documentation, dependency injection, routing, and request validation.
- **Pydantic** for typed request and response schemas.
- **PostgreSQL** as the production relational database.
- **SQLAlchemy 2.x** for ORM models, relationships, repository queries, and database sessions.
- **Alembic** for database migrations.
- **psycopg 3** as the PostgreSQL driver.
- **Python standard cryptography primitives** (`hashlib.scrypt`, `hmac`) for password hashing and JWT-style signed bearer tokens.
- **Pytest** and FastAPI `TestClient` for API-level tests.

## Project structure

```text
app/
  database.py          # Engine/session utilities
  dependencies.py      # Reusable FastAPI dependencies for DB, auth, and RBAC
  main.py              # FastAPI app factory and router registration
  models.py            # SQLAlchemy entities and relationships
  repositories/        # Database access layer
  routers/             # Route modules grouped by feature
  schemas/             # Pydantic request/response models
  services/            # Business rules and orchestration
migrations/            # Alembic migration environment and versions
tests/                 # Automated API tests
```

## Implemented requirements checklist

- User registration, login, and authenticated profile retrieval.
- JWT authentication with securely hashed passwords.
- `student` and `admin` role validation and RBAC enforcement.
- Inactive users cannot authenticate or access protected routes.
- Public active-course listing and active-course detail retrieval.
- Admin-only course creation, update, activation, deactivation, and deletion/soft-deactivation.
- Course `code` uniqueness and positive `capacity` validation.
- Student-only enrollment and deregistration.
- Duplicate enrollment prevention.
- Enrollment blocked when a course is full or inactive.
- Admin oversight: view all enrollments, view enrollments for a specific course, and remove a student from a course.
- Relational database models and relationships for users, courses, and enrollments.
- Alembic migration files.
- Automated endpoint coverage in `tests/test_api.py`.
- Cloud deployment files: `Dockerfile`, `render.yaml`, and `Procfile`.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Setup

```bash
git clone <your-repository-url>
cd Altschool-Capstone
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Create the PostgreSQL database locally:

```bash
createdb course_enrollment
```

If your PostgreSQL user, password, host, port, or database name differs, update `DATABASE_URL` in `.env`.

## Environment variables

| Variable | Default/example | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/course_enrollment` | SQLAlchemy PostgreSQL connection URL. |
| `JWT_SECRET` | generated 64-character development secret | Secret used to sign bearer tokens. Generate a new value for production. |
| `PORT` | `8000` | Port used by cloud platforms and Docker command. |

Generate a new 64-character JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Run migrations

```bash
alembic upgrade head
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

## Run the API locally

```bash
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000` by default. FastAPI's generated documentation is available at `/docs` and `/redoc`.

## API overview

### Authentication and users

- `POST /api/auth/register` registers a user. Body: `name`, `email`, `password`, optional `role` (`student` or `admin`).
- `POST /api/auth/login` returns a bearer token for valid credentials.
- `GET /api/users/me` returns the authenticated user's public profile.

### Courses

- `GET /api/courses` lists active courses.
- `GET /api/courses/{course_id}` returns an active course.
- `POST /api/courses` creates a course. Admin only.
- `PUT /api/courses/{course_id}` updates course title, code, and capacity. Admin only.
- `PATCH /api/courses/{course_id}/activate` activates a course. Admin only.
- `PATCH /api/courses/{course_id}/deactivate` deactivates a course. Admin only.
- `DELETE /api/courses/{course_id}` soft-deactivates a course. Admin only.

### Enrollments

- `POST /api/courses/{course_id}/enroll` enrolls the authenticated student.
- `DELETE /api/courses/{course_id}/enroll` deregisters the authenticated student.
- `GET /api/enrollments/me` lists the authenticated student's enrollments.
- `GET /api/admin/enrollments` lists all enrollments. Admin only.
- `GET /api/admin/courses/{course_id}/enrollments` lists enrollments for one course. Admin only.
- `DELETE /api/admin/courses/{course_id}/enrollments/{user_id}` removes a student from a course. Admin only.
- `GET /api/admin/stats` returns user, course, enrollment, and popular-course statistics. Admin only.

## Run tests

```bash
pytest
```

Tests use a temporary file-backed SQLite database through SQLAlchemy so the suite can run without requiring a local PostgreSQL service. Production and cloud configuration remain PostgreSQL.

## Cloud deployment

### Render blueprint deployment

1. Push this repository to GitHub.
2. Create a new Render Blueprint and point it at the repository.
3. Render will read `render.yaml`, create a PostgreSQL database, generate `JWT_SECRET`, build the Docker image, run `alembic upgrade head`, and start Uvicorn.
4. Confirm the service is healthy by visiting `/health` on the deployed URL.

### Generic Docker deployment

Build and run locally or on any container platform:

```bash
docker build -t course-enrollment-platform-api .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://postgres:postgres@host.docker.internal:5432/course_enrollment" \
  -e JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  course-enrollment-platform-api
```

The container command runs migrations before starting the API.
