import re
import json
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from core.models import TriageRequest, TriageResult, SeverityLevel
from core.triage import assess_severity
from data.models import TriageRecord, AgentTrace, EvidenceCitation, Patient, Condition, Encounter
from agents.base import CaseContext, SpecialistAssessment
from agents.intake_agent import IntakeAgent
from agents.specialty_router import SpecialtyRouter
from agents.specialists import get_specialist_agent
from agents.evidence_agent import EvidenceRetrievalAgent
from agents.explainability_agent import ExplainabilityAgent

logger = logging.getLogger(__name__)


def _calculate_age(birthdate_str: Optional[str]) -> Optional[int]:
    """Calculates age in years from Synthea YYYY-MM-DD birthdate string."""
    if not birthdate_str:
        return None
    try:
        from datetime import datetime
        bdate = datetime.strptime(birthdate_str[:10], "%Y-%m-%d")
        today = datetime.now()
        age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
        return age if 0 <= age <= 120 else None
    except Exception:
        return None


class MultiAgentOrchestrator:
    """
    Coordinates the autonomous clinical multi-agent decision support pipeline.
    Maintains an auditable, end-to-end trace (AgentTrace) for every decision step,
    strictly enforces deterministic safety triage, and short-circuits emergency cases.
    """

    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.router = SpecialtyRouter()
        self.evidence_agent = EvidenceRetrievalAgent()
        self.explainability_agent = ExplainabilityAgent()

    def process_case(
        self,
        raw_text: str,
        session: Session,
        patient_id: Optional[str] = None
    ) -> Tuple[TriageRecord, CaseContext]:
        """
        Executes the full clinical multi-agent workflow for conversational intake,
        integrating Synthea EHR patient context when patient_id is provided.
        """
        # Step 0: Synthea Patient Context Retrieval
        patient_name: Optional[str] = None
        patient_gender: Optional[str] = None
        patient_age: Optional[int] = None
        patient_history: list[str] = []
        patient_encounters: list[dict] = []
        patient_context_loaded: bool = False
        valid_patient_db_id: Optional[str] = None

        if patient_id:
            logger.info(f"Patient context requested: {patient_id}")
            try:
                patient = session.query(Patient).filter(Patient.id == patient_id.strip()).first()
                if patient:
                    valid_patient_db_id = patient.id
                    patient_name = patient.full_name
                    patient_gender = patient.gender
                    patient_age = _calculate_age(patient.birthdate)

                    # Retrieve diagnosed conditions
                    conditions = (
                        session.query(Condition)
                        .filter(Condition.patient_id == patient.id)
                        .order_by(Condition.start_date.desc())
                        .all()
                    )
                    patient_history = [c.description for c in conditions if c.description]

                    # Retrieve previous encounters
                    encounters = (
                        session.query(Encounter)
                        .filter(Encounter.patient_id == patient.id)
                        .order_by(Encounter.start_date.desc())
                        .limit(5)
                        .all()
                    )
                    patient_encounters = [
                        {
                            "id": e.id,
                            "description": e.description,
                            "class": e.encounter_class,
                            "date": e.start_date
                        }
                        for e in encounters
                    ]
                    patient_context_loaded = True
                    logger.info(
                        f"Patient context loaded: {patient_id} ({patient_name}, {patient_gender}). "
                        f"Conditions loaded: {len(patient_history)}. Encounters loaded: {len(patient_encounters)}."
                    )
                else:
                    logger.warning(f"Patient context requested for '{patient_id}', but no record was found in the Synthea database.")
            except Exception as e:
                logger.warning(f"Error retrieving Synthea patient context for '{patient_id}': {e}")
                patient_context_loaded = False
        else:
            logger.info("No patient_id provided; processing case without Synthea EHR context.")

        # Step 1: Intake Agent (NL -> Structured TriageRequest)
        triage_request = self.intake_agent.parse(raw_text)

        # If patient EHR age is available and intake default was used, sync with EHR age
        if patient_age and triage_request.age == 40 and "40" not in raw_text:
            triage_request.age = patient_age
        
        # Step 2: Deterministic Safety Triage Agent (STRICTLY RULE-BASED, ZERO LLM)
        triage_result = assess_severity(triage_request)

        # Step 3: Initialize DB Triage Record
        record = TriageRecord(
            patient_id=valid_patient_db_id,
            chief_complaint=raw_text[:500],
            symptoms=json.dumps(triage_request.symptoms),
            age=triage_request.age,
            duration_days=triage_request.duration_days,
            duration_hours=triage_request.duration_hours,
            severity=triage_result.severity.value,
            reason=triage_result.reason,
            score=triage_result.score,
            specialist=triage_result.specialist_suggestion.specialist if triage_result.specialist_suggestion else "General Medicine",
            narrative_summary=""
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        # Log Step 1 Trace: Intake
        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name="Intake Agent",
            input_summary=raw_text[:200],
            output_summary=f"Extracted symptoms: {triage_request.symptoms}, Age: {triage_request.age}, Duration: {triage_request.duration_days}d / {triage_request.duration_hours}h",
            reasoning="Converted natural language conversational narrative into structured triage parameters using taxonomy matching."
        )

        # Log EHR Context Trace if requested
        if patient_context_loaded:
            self._record_trace(
                session=session,
                case_id=record.id,
                agent_name="Synthea EHR Agent",
                input_summary=f"Synthea Patient ID: {patient_id}",
                output_summary=f"EHR Loaded: {patient_name} ({patient_gender}, Age {patient_age or 'N/A'}). {len(patient_history)} condition(s), {len(patient_encounters)} encounter(s).",
                reasoning=f"Active verified conditions: {', '.join(patient_history[:5]) if patient_history else 'None documented'}."
            )
        elif patient_id:
            self._record_trace(
                session=session,
                case_id=record.id,
                agent_name="Synthea EHR Agent",
                input_summary=f"Patient ID: {patient_id}",
                output_summary="Patient ID not found in Synthea EHR database.",
                reasoning="EHR context unavailable. Triaging proceeded on presenting narrative complaint only."
            )

        # Log Step 2 Trace: Deterministic Safety Triage
        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name="Safety Triage Agent",
            input_summary=f"Symptoms: {triage_request.symptoms}, Age: {triage_request.age}, Duration: {triage_request.duration_days}d / {triage_request.duration_hours}h",
            output_summary=f"Severity: {triage_result.severity.value} (Score: {triage_result.score}/100)",
            reasoning=f"Deterministic rule engine evaluation: {triage_result.reason}"
        )

        # Build Case Context
        case_ctx = CaseContext(
            raw_input=raw_text,
            request=triage_request,
            triage_result=triage_result,
            patient_id=valid_patient_db_id or patient_id,
            patient_name=patient_name,
            patient_age=patient_age or triage_request.age,
            patient_gender=patient_gender,
            patient_history=patient_history,
            patient_encounters=patient_encounters,
            patient_context_loaded=patient_context_loaded
        )

        # Check for EMERGENCY short-circuit
        if triage_result.severity == SeverityLevel.EMERGENCY:
            logger.warning(f"Case {record.id}: EMERGENCY detected. Initiating immediate short-circuit escalation.")
            
            self._record_trace(
                session=session,
                case_id=record.id,
                agent_name="Emergency Escalation Agent",
                input_summary=f"Critical red flags: {triage_result.matched_symptoms}",
                output_summary="EMERGENCY short-circuit triggered. Bypassing non-urgent specialist routing and RAG.",
                reasoning="Immediate life-safety escalation mandated by deterministic clinical safety protocol."
            )

            # Synthesize emergency referral
            summary = self.explainability_agent.generate_summary(case_ctx)
            case_ctx.narrative_summary = summary
            record.narrative_summary = summary
            record.specialist = "Emergency Medicine"
            session.commit()

            self._record_trace(
                session=session,
                case_id=record.id,
                agent_name="Explainability Agent",
                input_summary="Emergency short-circuit trace",
                output_summary="Generated immediate emergency referral and escalation report.",
                reasoning="Synthesized urgent stabilization directive and red-flag etiology rationale."
            )
            return record, case_ctx

        # Step 4: Non-Emergency Specialty Routing
        primary_specialty = self.router.get_primary_specialty(triage_request.symptoms)
        candidate_rankings = self.router.route(triage_request.symptoms)

        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name="Specialty Router Agent",
            input_summary=f"Symptoms: {triage_request.symptoms}",
            output_summary=f"Assigned Specialty: {primary_specialty} (Candidates: {candidate_rankings[:3]})",
            reasoning="Table-driven matching of presenting symptoms against the 100+ entry medical taxonomy."
        )

        # Step 5: Specialist Agent Pool
        specialist_agent = get_specialist_agent(primary_specialty)
        assessment: SpecialistAssessment = specialist_agent.assess(case_ctx)
        case_ctx.assessment = assessment
        record.specialist = assessment.specialty

        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name=f"{primary_specialty} Specialist Agent",
            input_summary=f"Case context with {len(triage_request.symptoms)} symptoms",
            output_summary=f"Impression: {assessment.primary_impression}; Differentials: {assessment.differential_diagnoses[:3]}",
            reasoning=assessment.clinical_reasoning
        )

        # Step 5b: Clinical Safety Floor (Mandate minimum HIGH severity for critical pathologies)
        critical_keywords = [
            "acs", "acute coronary syndrome", "myocardial infarction", "stemi", "nstemi",
            "heart attack", "stroke", "cerebrovascular accident", "cva",
            "transient ischemic attack", "tia", "aortic dissection"
        ]
        specialist_text = (
            (assessment.primary_impression or "") + " " +
            " ".join(assessment.differential_diagnoses or []) + " " +
            (assessment.clinical_reasoning or "")
        ).lower()

        matched_critical = [kw for kw in critical_keywords if re.search(r"\b" + re.escape(kw) + r"\b", specialist_text)]
        if matched_critical and record.severity in [SeverityLevel.LOW.value, SeverityLevel.MODERATE.value]:
            crit_name = matched_critical[0].upper()
            logger.warning(f"Case {record.id}: Safety floor triggered ({crit_name}). Escalating severity from {record.severity} to HIGH.")
            record.severity = SeverityLevel.HIGH.value
            record.score = max(record.score, 16)
            record.reason = f"Safety Floor Enforcement: Escalated to HIGH due to specialist identification of {crit_name}. ({record.reason})"
            case_ctx.triage_result.severity = SeverityLevel.HIGH
            case_ctx.triage_result.score = record.score
            session.commit()

            self._record_trace(
                session=session,
                case_id=record.id,
                agent_name="Safety Floor Agent",
                input_summary=f"Specialist findings contained critical pathology: {matched_critical}",
                output_summary=f"Enforced Safety Floor: Escalated severity to HIGH (Score: {record.score})",
                reasoning=f"Autonomous clinical safety floor prevents critical pathologies ({crit_name}) from being categorized as LOW or MODERATE."
            )

        # Step 6: Evidence Retrieval Agent (NCBI PubMed E-Utilities RAG)
        citations = self.evidence_agent.retrieve(
            evidence_terms=assessment.key_evidence_terms,
            session=session,
            case_id=record.id
        )
        case_ctx.citations = citations

        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name="Evidence Retrieval Agent",
            input_summary=f"PubMed Query Terms: {assessment.key_evidence_terms}",
            output_summary=f"Retrieved {len(citations)} peer-reviewed clinical citations from NCBI E-utilities.",
            reasoning="Formulated clinical search from specialist differential diagnosis and retrieved peer-reviewed abstracts."
        )

        # Step 7: Explainability / Summary Agent
        summary = self.explainability_agent.generate_summary(case_ctx)
        case_ctx.narrative_summary = summary
        record.narrative_summary = summary
        session.commit()

        self._record_trace(
            session=session,
            case_id=record.id,
            agent_name="Explainability Agent",
            input_summary="Full multi-agent decision trace",
            output_summary="Generated comprehensive referral report with embedded citations and diagnostic steps.",
            reasoning="Synthesized safety triage, specialist findings, and PubMed evidence into an explainable clinical referral."
        )

        return record, case_ctx

    def _record_trace(
        self,
        session: Session,
        case_id: int,
        agent_name: str,
        input_summary: str,
        output_summary: str,
        reasoning: str
    ) -> AgentTrace:
        trace = AgentTrace(
            case_id=case_id,
            agent_name=agent_name,
            input_summary=input_summary[:1000] if input_summary else None,
            output_summary=output_summary[:1000] if output_summary else None,
            reasoning=reasoning[:2000] if reasoning else None
        )
        session.add(trace)
        session.commit()
        return trace


# Global orchestrator instance
orchestrator = MultiAgentOrchestrator()
