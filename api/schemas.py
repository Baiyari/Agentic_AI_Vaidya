from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


class TriageRequestPayload(BaseModel):
    """
    Payload schema for incoming deterministic triage requests.
    """
    symptoms: List[str] = Field(..., min_length=1, description="List of patient symptoms.")
    age: int = Field(..., ge=0, le=120, description="Patient age.")
    duration_days: float = Field(default=1.0, ge=0, description="Symptom duration in days.")
    duration_hours: Optional[float] = Field(default=None, ge=0, description="Symptom duration in hours.")


class CaseCreatePayload(BaseModel):
    """
    Payload schema for natural language conversational intake.
    """
    text: str = Field(..., min_length=3, description="Unstructured clinical complaint or patient dialogue.")
    patient_id: Optional[str] = Field(None, description="Optional Synthea patient identifier.")


class AgentTraceResponse(BaseModel):
    id: int
    agent_name: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    reasoning: Optional[str] = None
    created_at: Optional[str] = None


class EvidenceCitationResponse(BaseModel):
    id: int
    pmid: Optional[str] = None
    title: str
    url: Optional[str] = None
    relevance_note: Optional[str] = None


class CaseDetailResponse(BaseModel):
    id: int
    patient_id: Optional[str] = None
    chief_complaint: Optional[str] = None
    symptoms: List[str]
    age: int
    duration_days: float
    duration_hours: Optional[float] = None
    severity: str
    score: int
    specialist: Optional[str] = None
    reason: str
    narrative_summary: Optional[str] = None
    created_at: str
    traces: List[AgentTraceResponse] = []
    citations: List[EvidenceCitationResponse] = []
