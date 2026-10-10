
from fastapi.testclient import TestClient

from loglens.api import app

client = TestClient(app)


def test_regression_groups_repeated_errors():
    response = client.post(
        "/regression",
        json={
            "logs": (
                "2026-10-10 10:00:01 ERROR Request timed out after 10 seconds\n"
                "2026-10-10 10:00:02 ERROR Request timed out after 20 seconds\n"
                "2026-10-10 10:00:03 ERROR Database connection failed"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["failure_count"] == 3
    assert data["unique_failure_groups"] == 2

    timeout_group = next(
        group for group in data["groups"]
        if "request timed out" in group["signature"]
    )

    assert timeout_group["count"] == 2
    assert timeout_group["line_numbers"] == [1, 2]


def test_regression_no_failures():
    response = client.post(
        "/regression",
        json={
            "logs": (
                "2026-10-10 10:00:01 INFO Application starting\n"
                "2026-10-10 10:00:02 INFO Application ready"
            )
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["failure_count"] == 0
    assert data["groups"] == []


def test_regression_rejects_empty_logs():
    response = client.post(
        "/regression",
        json={"logs": "   "},
    )

    assert response.status_code == 422


def test_regression_rejects_missing_logs():
    response = client.post("/regression", json={})

    assert response.status_code == 422
