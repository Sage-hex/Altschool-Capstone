from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    with TestClient(create_app(database_url=database_url, jwt_secret="test-secret")) as test_client:
        yield test_client


def register(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


def test_registration_login_and_profile_access(client: TestClient) -> None:
    registered = register(
        client,
        {"name": "Ada Lovelace", "email": "ada@example.com", "password": "secure-pass-123"},
    )

    assert registered["user"]["role"] == "student"
    assert registered["token_type"] == "bearer"

    logged_in = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "secure-pass-123"})
    assert logged_in.status_code == 200
    token = logged_in.json()["token"]

    profile = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["user"]["name"] == "Ada Lovelace"


def test_admin_course_management_and_public_browsing(client: TestClient) -> None:
    admin = register(client, {"name": "Admin User", "email": "admin@example.com", "password": "secure-pass-123", "role": "admin"})
    student = register(client, {"name": "Grace Hopper", "email": "grace@example.com", "password": "secure-pass-123"})

    course_payload = {
        "title": "Backend Engineering",
        "description": "Build reliable web APIs.",
        "instructor": "Prof. Linus",
        "capacity": 2,
    }
    forbidden = client.post("/api/courses", json=course_payload, headers={"Authorization": f"Bearer {student['token']}"})
    assert forbidden.status_code == 403

    created = client.post("/api/courses", json=course_payload, headers={"Authorization": f"Bearer {admin['token']}"})
    assert created.status_code == 201
    assert created.json()["course"]["available_seats"] == 2

    listed = client.get("/api/courses")
    assert listed.status_code == 200
    assert listed.json()["courses"][0]["title"] == "Backend Engineering"

    updated = client.put(
        f"/api/courses/{created.json()['course']['id']}",
        json={**course_payload, "title": "Advanced Backend Engineering", "capacity": 3},
        headers={"Authorization": f"Bearer {admin['token']}"},
    )
    assert updated.status_code == 200
    assert updated.json()["course"]["capacity"] == 3


def test_student_enrollment_rules_and_admin_reporting(client: TestClient) -> None:
    admin = register(client, {"name": "Enrollment Admin", "email": "enrollment-admin@example.com", "password": "secure-pass-123", "role": "admin"})
    student = register(client, {"name": "Katherine Johnson", "email": "katherine@example.com", "password": "secure-pass-123"})
    course = client.post(
        "/api/courses",
        json={"title": "Cloud Architecture", "description": "Design scalable cloud-native systems.", "instructor": "Dr. Hamilton", "capacity": 1},
        headers={"Authorization": f"Bearer {admin['token']}"},
    ).json()["course"]

    admin_enrollment = client.post(f"/api/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {admin['token']}"})
    assert admin_enrollment.status_code == 403

    enrolled = client.post(f"/api/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {student['token']}"})
    assert enrolled.status_code == 201
    assert enrolled.json()["enrollment"]["user_email"] == "katherine@example.com"

    duplicate = client.post(f"/api/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {student['token']}"})
    assert duplicate.status_code == 409

    mine = client.get("/api/enrollments/me", headers={"Authorization": f"Bearer {student['token']}"})
    assert mine.status_code == 200
    assert len(mine.json()["enrollments"]) == 1

    all_enrollments = client.get("/api/admin/enrollments", headers={"Authorization": f"Bearer {admin['token']}"})
    assert all_enrollments.status_code == 200
    assert len(all_enrollments.json()["enrollments"]) == 1

    stats = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin['token']}"})
    assert stats.status_code == 200
    assert stats.json()["stats"]["enrollments"]["active"] == 1


def test_validation_and_not_found_errors_have_consistent_shape(client: TestClient) -> None:
    invalid = client.post("/api/auth/register", json={"name": "A", "email": "not-an-email", "password": "short"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    missing = client.get("/api/courses/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "COURSE_NOT_FOUND"
