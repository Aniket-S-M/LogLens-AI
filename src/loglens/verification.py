
import re

from loglens.schemas import TriageReport


NUMBERED_LINE = re.compile(r"^\s*\[(\d+)\]\s?(.*)$")


def verify_evidence(
    report: TriageReport,
    original_log: str,
) -> list[str]:
    """Verify cited line numbers and excerpts against supplied logs."""
    indexed_lines: dict[int, str] = {}

    for physical_number, raw_line in enumerate(
        original_log.splitlines(), start=1
    ):
        match = NUMBERED_LINE.match(raw_line)

        if match:
            displayed_number = int(match.group(1))
            content = match.group(2)
        else:
            displayed_number = physical_number
            content = raw_line

        indexed_lines[displayed_number] = content

    errors: list[str] = []

    for diagnosis_index, diagnosis in enumerate(report.diagnoses):
        for evidence_index, item in enumerate(diagnosis.evidence):
            prefix = (
                f"diagnoses[{diagnosis_index}]"
                f".evidence[{evidence_index}]"
            )

            actual_line = indexed_lines.get(item.line_number)

            if actual_line is None:
                errors.append(
                    f"{prefix}: line {item.line_number} "
                    "does not exist"
                )
                continue

            if item.excerpt not in actual_line:
                errors.append(
                    f"{prefix}: excerpt does not match "
                    f"line {item.line_number}"
                )

    return errors
