# Course Enrollment Platform API Reference

This document is the comprehensive API contract for the Course Enrollment Platform. It documents authentication, request headers, request bodies, response bodies, error shapes, business rules, and example `curl` calls.

## Base URL

| Environment | Base URL |
| --- | --- |
| Local development | `http://127.0.0.1:8000` |
| Docker/local cloud-style run | `http://localhost:8000` |
| Deployed cloud app | Use your Render/service URL, for example `https://course-enrollment-platform-api.onrender.com` |

FastAPI also exposes generated interactive documentation at:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Authentication

Protected endpoints require a bearer token returned from register or login.

```http
Authorization: Bearer <token>
```

Tokens are HMAC-SHA256 JWT-style tokens signed with `JWT_SECRET`. Passwords are never stored directly; they are hashed with `hashlib.scrypt` and per-password random salts.

## Roles and permissions

| Action | Student | Admin |
| --- | --- | --- |
| Register/login/profile | ✅ | ✅ |
| View active courses | ✅ | ✅ |
| Enroll in a course | ✅ | ❌ |
| Deregister from a course | ✅ | ❌ |
| Create course | ❌ | ✅ |
| Update course | ❌ | ✅ |
| Activate/deactivate/delete course | ❌ | ✅ |
| View all enrollments | ❌ | ✅ |
| View course enrollments | ❌ | ✅ |
| Remove a student from a course | ❌ | ✅ |
| View admin stats | ❌ | ✅ |

## Shared conventions

### JSON headers

For requests with a body, send:

```http
Content-Type: application/json
```

### Success wrapper patterns

Most successful responses use a named top-level wrapper:

```json
{
  "user": {}
}
```

```json
{
  "course": {}
}
```

```json
{
  "enrollment": {}
}
```

```json
{
  "courses": []
}
```

```json
{
  "enrollments": []
}
```

### Error response shape

Application errors use this consistent shape:

```json
{
  "error": {
    "code": "COURSE_NOT_FOUND",
    "message": "Course not found."
  }
}
```

Validation errors use the same top-level shape and include `details` from FastAPI/Pydantic:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": []
  }
}
```

### Common status codes

| Status | Meaning |
| --- | --- |
| `200 OK` | Request completed successfully. |
| `201 Created` | Resource was created. |
| `204 No Content` | Resource/action completed and no response body is returned. |
| `401 Unauthorized` | Missing, invalid, or expired bearer token. |
| `403 Forbidden` | Authenticated user does not have the required role or is inactive. |
| `404 Not Found` | Requested resource does not exist or is not public/active. |
| `409 Conflict` | Business rule conflict such as duplicate email, duplicate course code, duplicate enrollment, full course, or inactive course. |
| `422 Unprocessable Entity` | Request body/path/query validation failed. |

## Data models

### User

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Generated primary key. |
| `name` | string | 2-100 characters. |
| `email` | string | Unique valid email address. |
| `role` | string | `student` or `admin`. Defaults to `student`. |
| `is_active` | boolean | Inactive users cannot authenticate or use protected routes. |
| `created_at` | datetime | Server-generated timestamp. |
| `updated_at` | datetime | Server-generated timestamp. |

`hashed_password` exists in the database but is never returned by the API.

### Course

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Generated primary key. |
| `title` | string | 3-150 characters. |
| `code` | string | Unique course code, 2-30 characters, normalized to uppercase. |
| `capacity` | integer | Must be greater than zero and no more than 10,000. |
| `is_active` | boolean | Public course reads only return active courses. |
| `available_seats` | integer | Computed from capacity minus current enrollment count. |
| `enrollment_count` | integer | Current enrollment count. |
| `created_by` | integer | Admin user ID that created the course. |
| `created_at` | datetime | Server-generated timestamp. |
| `updated_at` | datetime | Server-generated timestamp. |

### Enrollment

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Generated primary key. |
| `created_at` | datetime | Server-generated timestamp. |
| `user_id` | integer | Student user ID. |
| `user_name` | string | Student name. |
| `user_email` | string | Student email. |
| `course_id` | integer | Course ID. |
| `course_title` | string | Course title. |
| `course_code` | string | Course code. |

## Endpoints

### Health check

#### `GET /health`

Public endpoint used by local checks and cloud health probes.

**Authentication:** Not required.

**Request body:** None.

**Response `200 OK`:**

```json
{
  "status": "ok"
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/health
```

---

## Authentication and user management

### Register user

#### `POST /api/auth/register`

Creates a new active user and returns an authentication token.

**Authentication:** Not required.

**Business rules:**

- Email must be unique.
- Role must be either `student` or `admin`.
- Password must be 8-128 characters.
- Password is stored as a secure hash, never as plain text.

**Request body:**

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "secure-pass-123",
  "role": "student"
}
```

| Field | Required | Type | Validation |
| --- | --- | --- | --- |
| `name` | Yes | string | 2-100 characters. |
| `email` | Yes | string | Valid email and unique. |
| `password` | Yes | string | 8-128 characters. |
| `role` | No | string | `student` or `admin`; defaults to `student`. |

**Response `201 Created`:**

```json
{
  "user": {
    "id": 1,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "role": "student",
    "is_active": true,
    "created_at": "2026-06-04T12:00:00Z",
    "updated_at": "2026-06-04T12:00:00Z"
  },
  "token": "<bearer-token>",
  "token_type": "bearer"
}
```

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `409` | `EMAIL_ALREADY_REGISTERED` | Email is already registered. |
| `422` | `VALIDATION_ERROR` | Invalid name, email, password, or role. |

**Example:**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ada Lovelace","email":"ada@example.com","password":"secure-pass-123","role":"student"}'
```

### Login user

#### `POST /api/auth/login`

Authenticates an active user and returns a bearer token.

**Authentication:** Not required.

**Business rules:**

- Credentials must be valid.
- Inactive users cannot authenticate.

**Request body:**

```json
{
  "email": "ada@example.com",
  "password": "secure-pass-123"
}
```

| Field | Required | Type | Validation |
| --- | --- | --- | --- |
| `email` | Yes | string | Valid email. |
| `password` | Yes | string | 1-128 characters. |

**Response `200 OK`:** Same response shape as registration.

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `401` | `INVALID_CREDENTIALS` | Email or password is incorrect. |
| `403` | `USER_INACTIVE` | User exists but is inactive. |
| `422` | `VALIDATION_ERROR` | Invalid body. |

**Example:**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ada@example.com","password":"secure-pass-123"}'
```

### Retrieve profile

#### `GET /api/users/me`

Returns the authenticated user's public profile.

**Authentication:** Required.

**Request body:** None.

**Response `200 OK`:**

```json
{
  "user": {
    "id": 1,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "role": "student",
    "is_active": true,
    "created_at": "2026-06-04T12:00:00Z",
    "updated_at": "2026-06-04T12:00:00Z"
  }
}
```

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `401` | `AUTHENTICATION_REQUIRED` | Missing/invalid token. |
| `403` | `USER_INACTIVE` | User is inactive. |

**Example:**

```bash
curl http://127.0.0.1:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Course management

### List active courses

#### `GET /api/courses`

Returns all active courses. Deactivated courses are hidden from public course listing.

**Authentication:** Not required.

**Request body:** None.

**Response `200 OK`:**

```json
{
  "courses": [
    {
      "id": 1,
      "title": "Backend Engineering",
      "code": "BE101",
      "capacity": 30,
      "is_active": true,
      "available_seats": 29,
      "enrollment_count": 1,
      "created_by": 2,
      "created_at": "2026-06-04T12:00:00Z",
      "updated_at": "2026-06-04T12:00:00Z"
    }
  ]
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/api/courses
```

### Retrieve active course by ID

#### `GET /api/courses/{course_id}`

Returns one active course by ID. Inactive courses return `404` for public reads.

**Authentication:** Not required.

**Path parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `course_id` | integer | Course ID. |

**Request body:** None.

**Response `200 OK`:**

```json
{
  "course": {
    "id": 1,
    "title": "Backend Engineering",
    "code": "BE101",
    "capacity": 30,
    "is_active": true,
    "available_seats": 29,
    "enrollment_count": 1,
    "created_by": 2,
    "created_at": "2026-06-04T12:00:00Z",
    "updated_at": "2026-06-04T12:00:00Z"
  }
}
```

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `404` | `COURSE_NOT_FOUND` | Course does not exist or is inactive. |
| `422` | `VALIDATION_ERROR` | Invalid `course_id`. |

### Create course

#### `POST /api/courses`

Creates a new active course.

**Authentication:** Required.

**Authorization:** Admin only.

**Business rules:**

- Course code must be unique.
- Capacity must be greater than zero.
- Course code is normalized to uppercase.

**Request body:**

```json
{
  "title": "Backend Engineering",
  "code": "BE101",
  "capacity": 30
}
```

| Field | Required | Type | Validation |
| --- | --- | --- | --- |
| `title` | Yes | string | 3-150 characters. |
| `code` | Yes | string | 2-30 characters; unique; normalized uppercase. |
| `capacity` | Yes | integer | Greater than 0; max 10,000. |

**Response `201 Created`:**

```json
{
  "course": {
    "id": 1,
    "title": "Backend Engineering",
    "code": "BE101",
    "capacity": 30,
    "is_active": true,
    "available_seats": 30,
    "enrollment_count": 0,
    "created_by": 2,
    "created_at": "2026-06-04T12:00:00Z",
    "updated_at": "2026-06-04T12:00:00Z"
  }
}
```

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `401` | `AUTHENTICATION_REQUIRED` | Missing/invalid token. |
| `403` | `FORBIDDEN` | User is not an admin. |
| `409` | `COURSE_CODE_ALREADY_EXISTS` | Course code is already used. |
| `422` | `VALIDATION_ERROR` | Invalid title, code, or capacity. |

**Example:**

```bash
curl -X POST http://127.0.0.1:8000/api/courses \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Backend Engineering","code":"BE101","capacity":30}'
```

### Update course

#### `PUT /api/courses/{course_id}`

Updates a course's title, code, and capacity.

**Authentication:** Required.

**Authorization:** Admin only.

**Business rules:**

- Capacity cannot be lower than the current number of enrolled students.
- Code must remain unique.

**Request body:**

```json
{
  "title": "Advanced Backend Engineering",
  "code": "BE201",
  "capacity": 40
}
```

**Response `200 OK`:** Returns `{ "course": ... }`.

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `403` | `FORBIDDEN` | User is not an admin. |
| `404` | `COURSE_NOT_FOUND` | Course does not exist. |
| `409` | `COURSE_CODE_ALREADY_EXISTS` | Code is already used by another course. |
| `409` | `CAPACITY_BELOW_ENROLLMENT_COUNT` | Capacity is below current enrollments. |
| `422` | `VALIDATION_ERROR` | Invalid request body or path parameter. |

### Activate course

#### `PATCH /api/courses/{course_id}/activate`

Activates a course so it appears in public reads and can receive enrollments.

**Authentication:** Required.

**Authorization:** Admin only.

**Request body:** None.

**Response `200 OK`:** Returns `{ "course": ... }` with `is_active: true`.

### Deactivate course

#### `PATCH /api/courses/{course_id}/deactivate`

Deactivates a course so it is hidden from public reads and cannot receive enrollments.

**Authentication:** Required.

**Authorization:** Admin only.

**Request body:** None.

**Response `200 OK`:** Returns `{ "course": ... }` with `is_active: false`.

### Delete course

#### `DELETE /api/courses/{course_id}`

Soft-deletes a course by deactivating it. This keeps historical enrollment relationships intact.

**Authentication:** Required.

**Authorization:** Admin only.

**Request body:** None.

**Response `204 No Content`:** Empty response body.

---

## Enrollment management

### Enroll in a course

#### `POST /api/courses/{course_id}/enroll`

Enrolls the authenticated student in a course.

**Authentication:** Required.

**Authorization:** Student only.

**Business rules:**

- Admins cannot enroll.
- Course must exist.
- Course must be active.
- Course must not be full.
- Student cannot enroll in the same course twice.

**Request body:** None.

**Response `201 Created`:**

```json
{
  "enrollment": {
    "id": 1,
    "created_at": "2026-06-04T12:00:00Z",
    "user_id": 1,
    "user_name": "Ada Lovelace",
    "user_email": "ada@example.com",
    "course_id": 1,
    "course_title": "Backend Engineering",
    "course_code": "BE101"
  }
}
```

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `403` | `FORBIDDEN` | User is not a student. |
| `404` | `COURSE_NOT_FOUND` | Course does not exist. |
| `409` | `COURSE_INACTIVE` | Course is inactive. |
| `409` | `COURSE_FULL` | Course has no available seats. |
| `409` | `ALREADY_ENROLLED` | Student is already enrolled. |

**Example:**

```bash
curl -X POST http://127.0.0.1:8000/api/courses/1/enroll \
  -H "Authorization: Bearer $STUDENT_TOKEN"
```

### Deregister from a course

#### `DELETE /api/courses/{course_id}/enroll`

Removes the authenticated student's own enrollment from a course.

**Authentication:** Required.

**Authorization:** Student only.

**Request body:** None.

**Response `204 No Content`:** Empty response body.

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `403` | `FORBIDDEN` | User is not a student. |
| `404` | `COURSE_NOT_FOUND` | Course does not exist. |
| `404` | `ENROLLMENT_NOT_FOUND` | Student is not enrolled in the course. |

### Retrieve my enrollments

#### `GET /api/enrollments/me`

Lists enrollments for the authenticated student.

**Authentication:** Required.

**Authorization:** Student only.

**Request body:** None.

**Response `200 OK`:**

```json
{
  "enrollments": [
    {
      "id": 1,
      "created_at": "2026-06-04T12:00:00Z",
      "user_id": 1,
      "user_name": "Ada Lovelace",
      "user_email": "ada@example.com",
      "course_id": 1,
      "course_title": "Backend Engineering",
      "course_code": "BE101"
    }
  ]
}
```

---

## Administrative oversight

### View all enrollments

#### `GET /api/admin/enrollments`

Lists every enrollment in the system.

**Authentication:** Required.

**Authorization:** Admin only.

**Request body:** None.

**Response `200 OK`:** Returns `{ "enrollments": [...] }`.

### View enrollments for a specific course

#### `GET /api/admin/courses/{course_id}/enrollments`

Lists all enrollments for one course.

**Authentication:** Required.

**Authorization:** Admin only.

**Path parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `course_id` | integer | Course ID. |

**Request body:** None.

**Response `200 OK`:** Returns `{ "enrollments": [...] }`.

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `404` | `COURSE_NOT_FOUND` | Course does not exist. |

### Remove a student from a course

#### `DELETE /api/admin/courses/{course_id}/enrollments/{user_id}`

Admin-only removal of a student's enrollment from a course.

**Authentication:** Required.

**Authorization:** Admin only.

**Path parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `course_id` | integer | Course ID. |
| `user_id` | integer | Student user ID. |

**Request body:** None.

**Response `204 No Content`:** Empty response body.

**Possible errors:**

| Status | Code | Cause |
| --- | --- | --- |
| `404` | `COURSE_NOT_FOUND` | Course does not exist. |
| `404` | `ENROLLMENT_NOT_FOUND` | Student is not enrolled in that course. |

### View admin statistics

#### `GET /api/admin/stats`

Returns aggregate platform statistics and popular courses.

**Authentication:** Required.

**Authorization:** Admin only.

**Request body:** None.

**Response `200 OK`:**

```json
{
  "stats": {
    "users": {
      "total": 3,
      "students": 2,
      "admins": 1
    },
    "courses": {
      "total": 1,
      "active": 1
    },
    "enrollments": {
      "active": 2
    },
    "popular_courses": [
      {
        "id": 1,
        "title": "Backend Engineering",
        "code": "BE101",
        "capacity": 30,
        "is_active": true,
        "available_seats": 28,
        "enrollment_count": 2,
        "created_by": 2,
        "created_at": "2026-06-04T12:00:00Z",
        "updated_at": "2026-06-04T12:00:00Z"
      }
    ]
  }
}
```

## End-to-end manual flow

This quick flow demonstrates a complete happy path.

```bash
BASE_URL=http://127.0.0.1:8000

ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"name":"Admin User","email":"admin@example.com","password":"secure-pass-123","role":"admin"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')

STUDENT_TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"name":"Student User","email":"student@example.com","password":"secure-pass-123","role":"student"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')

curl -X POST "$BASE_URL/api/courses" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Backend Engineering","code":"BE101","capacity":30}'

curl "$BASE_URL/api/courses"

curl -X POST "$BASE_URL/api/courses/1/enroll" \
  -H "Authorization: Bearer $STUDENT_TOKEN"

curl "$BASE_URL/api/enrollments/me" \
  -H "Authorization: Bearer $STUDENT_TOKEN"

curl "$BASE_URL/api/admin/enrollments" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
