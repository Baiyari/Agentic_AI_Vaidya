from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from core.models import TriageRequest, TriageResult, SeverityLevel


class SpecialistAssessment(BaseModel):
    """
    Standardized clinical output schema produced by any specialist agent.
    """
    specialty: str = Field(..., description="Specialty name (e.g. Cardiology)")
    primary_impression: str = Field(..., description="Lead clinical impression / provisional diagnosis")
    differential_diagnoses: List[str] = Field(default_factory=list, description="Differential diagnoses considered")
    clinical_reasoning: str = Field(..., description="Detailed clinical reasoning and pathophysiology explanation")
    urgency_rating: str = Field(..., description="Urgency recommendation (EMERGENCY, URGENT, ROUTINE, SELF_CARE)")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended diagnostic tests or actions")
    key_evidence_terms: List[str] = Field(default_factory=list, description="Search queries / keywords for PubMed RAG")


class CaseContext(BaseModel):
    """
    Aggregated context passed through the multi-agent pipeline for a clinical case.
    """
    raw_input: str = Field(..., description="Unstructured patient narrative or complaint")
    request: TriageRequest = Field(..., description="Extracted structured triage parameters")
    triage_result: Optional[TriageResult] = Field(default=None, description="Deterministic safety triage result")
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    patient_history: List[str] = Field(default_factory=list, description="Prior conditions from EHR")
    patient_encounters: List[Dict[str, Any]] = Field(default_factory=list, description="Recent prior clinical encounters from EHR")
    patient_context_loaded: bool = Field(default=False, description="True if Synthea patient record was found and loaded")
    assessment: Optional[SpecialistAssessment] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    narrative_summary: Optional[str] = None


class BaseSpecialistAgent(ABC):
    """
    Abstract base class for all specialist agents.
    Provides shared clinical reasoning utilities, template-based deterministic fallbacks,
    and optional LLM enhancement hooks.
    """

    def __init__(self, specialty_name: str):
        self.specialty_name = specialty_name

    @abstractmethod
    def assess(self, case: CaseContext) -> SpecialistAssessment:
        """
        Conducts specialist clinical evaluation of the case.
        Must be implemented by each specialty subclass.
        """
        pass

    def _build_template_assessment(
        self,
        case: CaseContext,
        primary_impression: str,
        differentials: List[str],
        reasoning: str,
        recommended_actions: List[str],
        evidence_terms: List[str],
    ) -> SpecialistAssessment:
        """
        Constructs a consistent SpecialistAssessment instance, incorporating verified EHR history if available.
        """
        # Determine urgency rating derived from deterministic safety severity
        urgency = "ROUTINE"
        if case.triage_result:
            if case.triage_result.severity == SeverityLevel.EMERGENCY:
                urgency = "EMERGENCY"
            elif case.triage_result.severity == SeverityLevel.HIGH:
                urgency = "URGENT"
            elif case.triage_result.severity == SeverityLevel.MODERATE:
                urgency = "MODERATE"

        # Integrate verified Synthea EHR history into reasoning if present
        if case.patient_history:
            history_note = f"\n[EHR Medical History]: Patient has verified Synthea medical history of: {', '.join(case.patient_history[:5])}."
            if "[EHR Medical History]" not in reasoning:
                reasoning = reasoning + history_note

        return SpecialistAssessment(
            specialty=self.specialty_name,
            primary_impression=primary_impression,
            differential_diagnoses=differentials,
            clinical_reasoning=reasoning,
            urgency_rating=urgency,
            recommended_actions=recommended_actions,
            key_evidence_terms=evidence_terms
        )
