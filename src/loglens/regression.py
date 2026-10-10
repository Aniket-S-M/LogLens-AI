
import re
from collections import defaultdict

from loglens.parser import LogEvent, parse_log, level_is_error


def normalize_signature(message: str) -> str:
    """Normalize variable values so similar failures can be grouped."""
    signature = message.strip().lower()

    # Normalize common variable values.
    signature = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b",
        "<uuid>",
        signature,
    )
    signature = re.sub(r"\b0x[0-9a-f]+\b", "<address>", signature)
    signature = re.sub(r"\b\d+(?:\.\d+)?\b", "<number>", signature)
    signature = re.sub(r"\s+", " ", signature)

    return signature


def group_failures(log_text: str) -> dict:
    """Parse a regression log and group repeated error events."""
    events = parse_log(log_text)

    failures = [
        event for event in events
        if level_is_error(event.level)
    ]

    grouped = defaultdict(list)

    for event in failures:
        signature = normalize_signature(event.message)
        grouped[signature].append(event)

    failure_groups = []

    for signature, matching_events in grouped.items():
        first_event = matching_events[0]

        failure_groups.append({
            "signature": signature,
            "count": len(matching_events),
            "severity": first_event.level,
            "first_line": first_event.line_number,
            "line_numbers": [
                event.line_number for event in matching_events
            ],
            "examples": [
                event.message for event in matching_events[:3]
            ],
        })

    failure_groups.sort(
        key=lambda group: group["count"],
        reverse=True,
    )

    return {
        "total_events": len(events),
        "failure_count": len(failures),
        "unique_failure_groups": len(failure_groups),
        "status": "failures_detected" if failures else "no_failures_detected",
        "groups": failure_groups,
    }
