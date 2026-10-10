
from loglens.rag_guard import has_explicit_failure


def test_detects_error():
    logs = "[1] 2026-10-10 10:00:01 ERROR Database connection failed"
    assert has_explicit_failure(logs) is True


def test_detects_critical():
    logs = "[1] CRITICAL Service unavailable"
    assert has_explicit_failure(logs) is True


def test_detects_exception():
    logs = "[1] ConnectionError: Connection refused"
    assert has_explicit_failure(logs) is True


def test_healthy_logs_have_no_explicit_failure():
    logs = (
        "[1] INFO Application starting\n"
        "[2] INFO Application ready"
    )
    assert has_explicit_failure(logs) is False
