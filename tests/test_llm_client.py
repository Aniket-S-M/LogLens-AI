
import os
import pytest
from loglens.llm_client import analyze_logs

@pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_TESTS") != "1",
    reason="Requires a running Ollama server and the phi3:mini model",
)
def test_phi3_analyzes_sample_failure():
    logs = (
        "[3] 2026-10-09 10:00:03 ERROR Database connection failed\n"
        "[4] Traceback (most recent call last):\n"
        "[5] ConnectionError: Connection refused"
    )

    report, metrics = analyze_logs(logs)

    print("\nREPORT STATUS:", report.status)
    print("\nFULL REPORT:")
    print(report.model_dump_json(indent=2))
    print("\nMETRICS:", metrics)

    # Temporary diagnostic assertion
    assert report.status in {"success", "insufficient_evidence"}

    assert report.status == "success"
    assert len(report.diagnoses) >= 1

    diagnosis = report.diagnoses[0]
    assert diagnosis.evidence
    assert any(
        "Connection refused" in item.excerpt
        or "Database connection failed" in item.excerpt
        for item in diagnosis.evidence
    )

    assert metrics["model"] == "phi3:mini"
    assert metrics["latency_ms"] > 0
