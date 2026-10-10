
import re

ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|EXCEPTION)\b",
    re.IGNORECASE,
)

EXCEPTION_PATTERN = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)\s*:",
)


def has_explicit_failure(logs: str) -> bool:
    """Return True when a log line explicitly signals a failure."""
    return any(
        ERROR_PATTERN.search(line) or EXCEPTION_PATTERN.search(line)
        for line in logs.splitlines()
    )
