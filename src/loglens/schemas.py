
from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    line_number: int = Field(ge=1)
    excerpt: str = Field(min_length=1)


class FailureDiagnosis(BaseModel):
    title: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "critical"]
    summary: str = Field(min_length=1)
    likely_cause: str = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    uncertainty: str = Field(min_length=1)


class TriageReport(BaseModel):
    status: Literal["success", "insufficient_evidence"]
    diagnoses: list[FailureDiagnosis]

class HistoricalIncidentReference(BaseModel):
    incident_id: str = Field(min_length=1)
    connection: str = Field(min_length=1)


class RagTriageReport(BaseModel):
    status: Literal["success", "insufficient_evidence"]
    diagnoses: list[FailureDiagnosis]
    related_incidents: list[HistoricalIncidentReference]
