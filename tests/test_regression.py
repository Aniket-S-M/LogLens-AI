
from loglens.regression import group_failures, normalize_signature


def test_repeated_errors_are_grouped():
    logs = (
        "2026-10-10 10:00:01 ERROR Request timed out after 10 seconds\n"
        "2026-10-10 10:00:02 ERROR Request timed out after 20 seconds\n"
        "2026-10-10 10:00:03 ERROR Database connection failed"
    )

    report = group_failures(logs)

    assert report["failure_count"] == 3
    assert report["unique_failure_groups"] == 2

    timeout_group = next(
        group for group in report["groups"]
        if "request timed out" in group["signature"]
    )

    assert timeout_group["count"] == 2
    assert timeout_group["line_numbers"] == [1, 2]


def test_distinct_errors_remain_separate():
    logs = (
        "2026-10-10 10:00:01 ERROR Permission denied\n"
        "2026-10-10 10:00:02 ERROR Database connection failed"
    )

    report = group_failures(logs)

    assert report["unique_failure_groups"] == 2


def test_no_failures_returns_empty_groups():
    logs = (
        "2026-10-10 10:00:01 INFO Application starting\n"
        "2026-10-10 10:00:02 INFO Application ready"
    )

    report = group_failures(logs)

    assert report["failure_count"] == 0
    assert report["unique_failure_groups"] == 0
    assert report["groups"] == []
    assert report["status"] == "no_failures_detected"


def test_signature_normalizes_numbers():
    first = normalize_signature("Retry failed after 3 seconds")
    second = normalize_signature("Retry failed after 8 seconds")

    assert first == second
