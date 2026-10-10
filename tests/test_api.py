
from fastapi.testclient import TestClient

from loglens.api import app, analyze
from loglens.llm_client import OllamaClientError

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_rejects_empty_logs():
    response = client.post(
        "/analyze",
        json={"logs": ""},
    )

    assert response.status_code == 422


def test_analyze_rejects_missing_logs():
    response = client.post("/analyze", json={})

    assert response.status_code == 422


def test_analyze_returns_report(monkeypatch):
    def fake_analyze_logs(numbered_logs):
        assert "[1]" in numbered_logs

        return (
            {
                "status": "success",
                "diagnoses": [],
            },
            {
                "model": "test-model",
                "latency_ms": 1.0,
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        )

    # Build a valid Pydantic report for the mocked response.
    from loglens.schemas import TriageReport

    def fake_analyze_logs(numbered_logs):
        assert "[1]" in numbered_logs

        report = TriageReport(
            status="success",
            diagnoses=[],
        )
        metrics = {
            "model": "test-model",
            "latency_ms": 1.0,
            "prompt_tokens": 10,
            "completion_tokens": 5,
        }
        return report, metrics

    monkeypatch.setattr(
        "loglens.api.analyze_logs",
        fake_analyze_logs,
    )

    response = client.post(
        "/analyze",
        json={"logs": "ERROR Database connection failed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report"]["status"] == "success"
    assert body["metrics"]["model"] == "test-model"


def test_analyze_handles_ollama_failure(monkeypatch):
    def fake_analyze_logs(numbered_logs):
        raise OllamaClientError("Ollama unavailable")

    monkeypatch.setattr(
        "loglens.api.analyze_logs",
        fake_analyze_logs,
    )

    response = client.post(
        "/analyze",
        json={"logs": "ERROR Database connection failed"},
    )

    assert response.status_code == 502
    assert "Ollama unavailable" in response.json()["detail"]
