from pathlib import Path


def test_api_reference_documents_all_routes_and_request_bodies() -> None:
    docs = Path("docs/API_REFERENCE.md").read_text()

    required_sections = [
        "GET /health",
        "POST /api/auth/register",
        "POST /api/auth/login",
        "GET /api/users/me",
        "GET /api/courses",
        "GET /api/courses/{course_id}",
        "POST /api/courses",
        "PUT /api/courses/{course_id}",
        "PATCH /api/courses/{course_id}/activate",
        "PATCH /api/courses/{course_id}/deactivate",
        "DELETE /api/courses/{course_id}",
        "POST /api/courses/{course_id}/enroll",
        "DELETE /api/courses/{course_id}/enroll",
        "GET /api/enrollments/me",
        "GET /api/admin/enrollments",
        "GET /api/admin/courses/{course_id}/enrollments",
        "DELETE /api/admin/courses/{course_id}/enrollments/{user_id}",
        "GET /api/admin/stats",
        "Request body",
        "Authorization: Bearer <token>",
        "Error response shape",
    ]

    for section in required_sections:
        assert section in docs
