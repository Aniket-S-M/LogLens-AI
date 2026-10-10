
import re
from dataclasses import dataclass, asdict
from typing import Optional


LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})"
    r"\s+(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)"
    r"\s+(?P<message>.*)$",
    re.IGNORECASE,
)


@dataclass
class LogEvent:
    line_number: int
    timestamp: Optional[str]
    level: str
    message: str
    raw_lines: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def parse_log(text: str) -> list[LogEvent]:
    """Parse timestamped logs and attach multiline tracebacks to their events."""
    events: list[LogEvent] = []
    current: Optional[LogEvent] = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if not line.strip():
            continue

        match = LOG_PATTERN.match(line)

        if match:
            if current is not None:
                events.append(current)

            level = match.group("level").upper()
            if level == "WARN":
                level = "WARNING"

            current = LogEvent(
                line_number=line_number,
                timestamp=match.group("timestamp"),
                level=level,
                message=match.group("message"),
                raw_lines=[line],
            )
        elif current is not None:
            # Attach continuation lines and Python traceback frames
            # to the preceding event.
            current.raw_lines.append(line)
            if level_is_error(current.level):
                current.message += "\n" + line
        else:
            # Preserve unstructured lines instead of silently dropping them.
            current = LogEvent(
                line_number=line_number,
                timestamp=None,
                level="UNKNOWN",
                message=line,
                raw_lines=[line],
            )

    if current is not None:
        events.append(current)

    return events


def level_is_error(level: str) -> bool:
    return level in {"ERROR", "CRITICAL"}


def summarize_events(events: list[LogEvent]) -> dict:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.level] = counts.get(event.level, 0) + 1

    failures = [
        event.to_dict()
        for event in events
        if level_is_error(event.level)
    ]

    return {
        "total_events": len(events),
        "level_counts": counts,
        "failure_count": len(failures),
        "failures": failures,
    }
