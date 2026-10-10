
import re
from loglens.incident_store import IncidentRetriever
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from loglens.rag_client import analyze_logs_with_history
from loglens.llm_client import analyze_logs, OllamaClientError
from loglens.regression import group_failures


def number_log_lines(logs: str) -> str:
    """Assign consistent line numbers to submitted logs."""
    numbered_lines = []

    for line_number, line in enumerate(logs.splitlines(), start=1):
        # Remove an existing [N] prefix to avoid double numbering.
        clean_line = re.sub(r"^\s*\[\d+\]\s?", "", line)
        numbered_lines.append(f"[{line_number}] {clean_line}")

    return "\n".join(numbered_lines)


app = FastAPI(
    title="LogLens AI",
    description="AI-powered log analysis and regression triage",
    version="0.2.0",
)
_incident_retriever = None


def get_incident_retriever() -> IncidentRetriever:
    global _incident_retriever

    if _incident_retriever is None:
        retriever = IncidentRetriever()
        retriever.index_incidents()
        _incident_retriever = retriever

    return _incident_retriever

class AnalyzeRequest(BaseModel):
    logs: str = Field(
        min_length=1,
        max_length=100_000,
        description="Raw application logs to analyze",
    )
class IncidentSearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=10_000,
        description="Error message or failure description to search",
    )
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Search query must not be blank")
        return value

class RegressionRequest(BaseModel):
    logs: str = Field(
        min_length=1,
        max_length=100_000,
        description="Logs from a test or regression run",
    )

    @field_validator("logs")
    @classmethod
    def logs_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Logs must not be blank")
        return value


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "LogLens AI",
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        numbered_logs = number_log_lines(request.logs)
        report, metrics = analyze_logs(numbered_logs)

        return {
            "report": report.model_dump(),
            "metrics": metrics,
        }

    except OllamaClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.post("/regression")
def analyze_regression(request: RegressionRequest):
    try:
        # Pass raw logs so the parser can recognize timestamps correctly.
        return group_failures(request.logs)

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Regression analysis failed: {exc}",
        ) from exc
@app.post("/incidents/search")
def search_incidents(request: IncidentSearchRequest):
    try:
        retriever = get_incident_retriever()
        matches = retriever.search(
            request.query,
            top_k=request.top_k,
        )

        return {
            "query": request.query,
            "match_count": len(matches),
            "matches": matches,
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Incident search failed: {exc}",
        ) from exc

@app.post("/analyze-rag")
def analyze_rag(request: AnalyzeRequest):
    try:
        numbered_logs = number_log_lines(request.logs)

        # Retrieve historical context.
        retriever = get_incident_retriever()
        matches = retriever.search(
            request.logs,
            top_k=3,
        )

        # Keep only the retrieved incidents' context fields.
        incidents = [
            {
                "id": match["id"],
                "title": match["title"],
                "category": match["category"],
                "symptoms": match["symptoms"],
                "root_cause": match["root_cause"],
                "resolution": match["resolution"],
                "source": match["source"],
            }
            for match in matches
        ]

        report, metrics = analyze_logs_with_history(
            numbered_logs=numbered_logs,
            incidents=incidents,
            debug=True,
        )

        return {
            "report":report.model_dump(),
            "metrics":metrics,
        }

    except OllamaClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
