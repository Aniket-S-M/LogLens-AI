
import json
import time

import httpx

from loglens.schemas import TriageReport
from loglens.verification import verify_evidence


OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "phi3:mini"


SYSTEM_PROMPT = """
You are LogLens AI, a software failure triage assistant.

Analyze the supplied logs and identify supported software failures.

Rules:
1. Treat ERROR and CRITICAL entries as evidence of potential failures.
2. If logs explicitly report an error or exception, diagnose the observed
   failure even when its deeper root cause is unknown.
3. Distinguish the observed failure from its suspected underlying cause.
4. Never invent log lines, timestamps, exceptions, or stack traces.
5. Every diagnosis must cite exact supplied line numbers and excerpts.
6. Use "insufficient_evidence" with an empty diagnoses list only when
   the logs contain no identifiable failure or actionable error evidence.
7. If the failure is clear but its root cause is uncertain, describe the
   failure and state that the underlying cause is uncertain.
8. Return only JSON matching the requested schema.
9. Do not execute commands or claim that you fixed a problem.
"""



class OllamaClientError(RuntimeError):
    """Raised when local model inference fails."""


def analyze_logs(
    numbered_logs: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 120.0,
) -> tuple[TriageReport, dict]:
    """Analyze numbered log lines and validate the model response."""
    started = time.perf_counter()

    prompt = f"""
Analyze the following numbered log lines.

Return a JSON object with:
- status: "success" or "insufficient_evidence"
- diagnoses: a list of objects containing:
  title, severity, summary, likely_cause,
  recommended_actions, evidence, uncertainty

Each evidence item must contain:
- line_number: integer
- excerpt: exact text from the corresponding log line

If evidence is insufficient, use an empty diagnoses list.

LOGS:
{numbered_logs}
"""

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    "stream": False,
                    "format": TriageReport.model_json_schema(),
                    "options": {"temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()

        content = payload["message"]["content"]
        report = TriageReport.model_validate_json(content)

        # Verify that the model's evidence exists in the supplied logs.
        evidence_errors = verify_evidence(
            report,
            numbered_logs,
        )

        if evidence_errors:
            raise ValueError(
                "LLM returned unverifiable evidence: "
                + "; ".join(evidence_errors)
            )

        # Enforce consistency between status and diagnoses.
        if (
            report.status == "insufficient_evidence"
            and report.diagnoses
        ):
            raise ValueError(
                "Insufficient-evidence report must have no diagnoses"
            )

        elapsed_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        metrics = {
            "model": model,
            "latency_ms": elapsed_ms,
            "prompt_tokens": payload.get(
                "prompt_eval_count", 0
            ),
            "completion_tokens": payload.get(
                "eval_count", 0
            ),
        }

        return report, metrics

    except (
        httpx.HTTPError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise OllamaClientError(
            f"Log analysis failed: {exc}"
        ) from exc
