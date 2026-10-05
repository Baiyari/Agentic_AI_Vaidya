from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class SeverityLevel(str, Enum):
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"

class TriageRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1, description="List of symptoms reported by the patient.")
    age: int = Field(..., ge=0, le=120, description="Age of the patient in years.")
    duration_days: float = Field(default=1.0, ge=0, description="Duration of symptoms in days (supports fractional days).")
    duration_hours: Optional[float] = Field(default=None, ge=0, description="Duration of symptoms in hours.")

class SpecialistSuggestion(BaseModel):
    category: str
    specialist: str

class TriageResult(BaseModel):
    severity: SeverityLevel
    reason: str
    matched_symptoms: List[str]
    score: int
    specialist_suggestion: Optional[SpecialistSuggestion] = None
