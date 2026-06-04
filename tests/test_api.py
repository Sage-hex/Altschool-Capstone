from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    with TestClient(create_app(database_url=database_url, jwt_secret="test-secret", create_tables=True)) as test_client:
        yield test_client


def register(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def course_payload(code: str = "BE101", capacity: int = 2) -> dict[str, object]:
    return {"title": "Backend Engineering", "code": code, "capacity": capacity}


def test_health_registration_login_and_profile_access(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

    registered = register(client, {"name": "Ada Lovelace", "email": "ada@example.com", "password": "secure-pass-123"})
    assert registered["user"]["role"] == "student"
    assert registered["user"]["is_active"] is True
    assert registered["token_type"] == "bearer"

    duplicate = client.post("/api/auth/register", json={"name": "Ada Again", "email": "ada@example.com", "password": "secure-pass-123"})
    assert duplicate.status_code == 409

    logged_in = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "secure-pass-123"})
    assert logged_in.status_code == 200
    token = logged_in.json()["token"]

    profile = client.get("/api/users/me", headers=auth_header(token))
    assert profile.status_code == 200
    assert profile.json()["user"]["name"] == "Ada Lovelace"


def test_admin_course_management_and_public_browsing(client: TestClient) -> None:
    admin = register(client, {"name": "Admin User", "email": "admin@example.com", "password": "secure-pass-123", "role": "admin"})
    student = register(client, {"name": "Grace Hopper", "email": "grace@example.com", "password": "secure-pass-123"})

    forbidden = client.post("/api/courses", json=course_payload(), headers=auth_header(student["token"]))
    assert forbidden.status_code == 403

    created = client.post("/api/courses", json=course_payload(), headers=auth_header(admin["token"]))
    assert created.status_code == 201
    course = created.json()["course"]
    assert course["code"] == "BE101"
    assert course["available_seats"] == 2

    duplicate_code = client.post("/api/courses", json=course_payload(), headers=auth_header(admin["token"]))
    assert duplicate_code.status_code == 409

    listed = client.get("/api/courses")
    assert listed.status_code == 200
    assert listed.json()["courses"][0]["title"] == "Backend Engineering"

    fetched = client.get(f"/api/courses/{course['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["course"]["code"] == "BE101"

    updated = client.put(
        f"/api/courses/{course['id']}",
        json={"title": "Advanced Backend Engineering", "code": "BE201", "capacity": 3},
        headers=auth_header(admin["token"]),
    )
    assert updated.status_code == 200
    assert updated.json()["course"]["capacity"] == 3
    assert updated.json()["course"]["code"] == "BE201"

    deactivated = client.patch(f"/api/courses/{course['id']}/deactivate", headers=auth_header(admin["token"]))
    assert deactivated.status_code == 200
    assert deactivated.json()["course"]["is_active"] is False
    assert client.get(f"/api/courses/{course['id']}").status_code == 404

    activated = client.patch(f"/api/courses/{course['id']}/activate", headers=auth_header(admin["token"]))
    assert activated.status_code == 200
    assert activated.json()["course"]["is_active"] is True

    deleted = client.delete(f"/api/courses/{course['id']}", headers=auth_header(admin["token"]))
    assert deleted.status_code == 204
    assert client.get(f"/api/courses/{course['id']}").status_code == 404


def test_student_enrollment_rules_deregistering_and_admin_oversight(client: TestClient) -> None:
    admin = register(client, {"name": "Enrollment Admin", "email": "enrollment-admin@example.com", "password": "secure-pass-123", "role": "admin"})
    student = register(client, {"name": "Katherine Johnson", "email": "katherine@example.com", "password": "secure-pass-123"})
    second_student = register(client, {"name": "Dorothy Vaughan", "email": "dorothy@example.com", "password": "secure-pass-123"})
    course = client.post("/api/courses", json={"title": "Cloud Architecture", "code": "CLD101", "capacity": 1}, headers=auth_header(admin["token"])).json()["course"]

    admin_enrollment = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(admin["token"]))
    assert admin_enrollment.status_code == 403

    enrolled = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(student["token"]))
    assert enrolled.status_code == 201
    assert enrolled.json()["enrollment"]["user_email"] == "katherine@example.com"

    duplicate = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(student["token"]))
    assert duplicate.status_code == 409

    full = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(second_student["token"]))
    assert full.status_code == 409

    mine = client.get("/api/enrollments/me", headers=auth_header(student["token"]))
    assert mine.status_code == 200
    assert len(mine.json()["enrollments"]) == 1

    all_enrollments = client.get("/api/admin/enrollments", headers=auth_header(admin["token"]))
    assert all_enrollments.status_code == 200
    assert len(all_enrollments.json()["enrollments"]) == 1

    course_enrollments = client.get(f"/api/admin/courses/{course['id']}/enrollments", headers=auth_header(admin["token"]))
    assert course_enrollments.status_code == 200
    assert course_enrollments.json()["enrollments"][0]["course_code"] == "CLD101"

    stats = client.get("/api/admin/stats", headers=auth_header(admin["token"]))
    assert stats.status_code == 200
    assert stats.json()["stats"]["enrollments"]["active"] == 1

    removed = client.delete(f"/api/admin/courses/{course['id']}/enrollments/{student['user']['id']}", headers=auth_header(admin["token"]))
    assert removed.status_code == 204

    re_enrolled = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(student["token"]))
    assert re_enrolled.status_code == 201

    deregistered = client.delete(f"/api/courses/{course['id']}/enroll", headers=auth_header(student["token"]))
    assert deregistered.status_code == 204
    assert client.get("/api/enrollments/me", headers=auth_header(student["token"])).json()["enrollments"] == []


def test_inactive_courses_validation_and_not_found_errors(client: TestClient) -> None:
    admin = register(client, {"name": "Admin", "email": "admin2@example.com", "password": "secure-pass-123", "role": "admin"})
    student = register(client, {"name": "Student", "email": "student@example.com", "password": "secure-pass-123"})
    course = client.post("/api/courses", json={"title": "Data Systems", "code": "DATA101", "capacity": 1}, headers=auth_header(admin["token"])).json()["course"]

    invalid = client.post("/api/auth/register", json={"name": "A", "email": "not-an-email", "password": "short"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    client.patch(f"/api/courses/{course['id']}/deactivate", headers=auth_header(admin["token"]))
    inactive_enrollment = client.post(f"/api/courses/{course['id']}/enroll", headers=auth_header(student["token"]))
    assert inactive_enrollment.status_code == 409
    assert inactive_enrollment.json()["error"]["code"] == "COURSE_INACTIVE"

    missing = client.get("/api/courses/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "COURSE_NOT_FOUND"
