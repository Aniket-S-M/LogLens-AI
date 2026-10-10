
from pathlib import Path

from loglens.parser import parse_log, summarize_events


def test_parse_log_levels_and_timestamps():
    text = (
        "2026-10-09 10:00:01 INFO Started\n"
        "2026-10-09 10:00:02 ERROR Failed\n"
    )

    events = parse_log(text)

    assert len(events) == 2
    assert events[0].level == "INFO"
    assert events[1].level == "ERROR"
    assert events[1].line_number == 2


def test_warn_alias_is_normalized():
    events = parse_log("2026-10-09 10:00:01 WARN Retrying")

    assert events[0].level == "WARNING"


def test_traceback_is_attached_to_error():
    text = (
        "2026-10-09 10:00:01 ERROR Request failed\n"
        '  File "app.py", line 42, in connect\n'
        "ConnectionError: Connection refused\n"
    )

    events = parse_log(text)

    assert len(events) == 1
    assert "ConnectionError: Connection refused" in events[0].message
    assert len(events[0].raw_lines) == 3


def test_unstructured_line_is_preserved():
    events = parse_log("unexpected startup output")

    assert len(events) == 1
    assert events[0].level == "UNKNOWN"
    assert events[0].message == "unexpected startup output"


def test_summary_counts_failures():
    events = parse_log(
        "2026-10-09 10:00:01 INFO Started\n"
        "2026-10-09 10:00:02 ERROR Failed\n"
        "2026-10-09 10:00:03 CRITICAL Crashed\n"
    )

    summary = summarize_events(events)

    assert summary["total_events"] == 3
    assert summary["failure_count"] == 2


def test_sample_log_contains_expected_failure():
    sample_path = Path("samples/application.log")
    events = parse_log(sample_path.read_text(encoding="utf-8"))

    summary = summarize_events(events)

    assert summary["failure_count"] == 2
    assert any(
        "ConnectionError" in event["message"]
        for event in summary["failures"]
    )
