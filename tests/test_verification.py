
from loglens.schemas import Evidence, FailureDiagnosis, TriageReport
from loglens.verification import verify_evidence


def make_report(line_number: int, excerpt: str) -> TriageReport:
    return TriageReport(
        status="success",
        diagnoses=[
            FailureDiagnosis(
                title="Database failure",
                severity="high",
                summary="Database connection was refused.",
                likely_cause="The database may be unavailable.",
                recommended_actions=["Check database availability."],
                evidence=[
                    Evidence(
                        line_number=line_number,
                        excerpt=excerpt,
                    )
                ],
                uncertainty="The exact root cause is not confirmed.",
            )
        ],
    )


def test_valid_evidence_passes():
    log = "INFO Started\nERROR Connection refused"

    report = make_report(2, "Connection refused")

    assert verify_evidence(report, log) == []


def test_fabricated_excerpt_is_rejected():
    log = "INFO Started\nERROR Connection refused"

    report = make_report(2, "Password was incorrect")

    errors = verify_evidence(report, log)

    assert len(errors) == 1
    assert "does not match" in errors[0]


def test_nonexistent_line_is_rejected():
    log = "ERROR Connection refused"

    report = make_report(5, "Connection refused")

    errors = verify_evidence(report, log)

    assert len(errors) == 1
    assert "does not exist" in errors[0]
