import logging
from typing import List, Dict, Any, Optional

from agents.base import CaseContext
from agents.llm_client import llm_client
from core.models import SeverityLevel

logger = logging.getLogger(__name__)


class ExplainabilityAgent:
    """
    Synthesizes the entire multi-agent trace into a structured, explainable referral
    and escalation summary for clinicians and patients, with embedded PubMed citations.
    """

    def generate_summary(self, case: CaseContext) -> str:
        """
        Synthesizes the case findings into a clinician-grade referral report.
        """
        # If Gemini is available, attempt narrative generation
        if llm_client.is_available():
            llm_summary = self._generate_with_llm(case)
            if llm_summary:
                return llm_summary

        # Deterministic structured clinical template
        return self._generate_template(case)

    def _generate_with_llm(self, case: CaseContext) -> Optional[str]:
        triage = case.triage_result
        assessment = case.assessment
        citations = case.citations

        # Format patient context for LLM
        if case.patient_context_loaded:
            conditions_list = []
            for c in case.patient_history:
                conditions_list.append(c.get("description", str(c)) if isinstance(c, dict) else str(c))
            conditions_str = ", ".join(conditions_list) if conditions_list else "None recorded"

            encounters_list = []
            for e in case.patient_encounters[:3]:
                if isinstance(e, dict):
                    encounters_list.append(f"{e.get('description', '')} ({e.get('date', '')})")
                else:
                    encounters_list.append(str(e))
            encounters_str = ", ".join(encounters_list) if encounters_list else "None recorded"

            patient_context_info = (
                f"- Synthea Patient EHR Context: ID={case.patient_id}, Name={case.patient_name}, "
                f"Age={case.patient_age}, Gender={case.patient_gender}\n"
                f"- Recorded Conditions: {conditions_str}\n"
                f"- Recent Encounters: {encounters_str}"
            )
        else:
            patient_context_info = "- Synthea Patient EHR Context: Not provided / unavailable"

        prompt = (
            f"You are the Lead Clinical Explainability Officer for Vaidya. "
            f"Synthesize the following case into a formal clinical referral summary:\n"
            f"{patient_context_info}\n"
            f"- Current Presentation: {case.raw_input} (Symptoms: {case.request.symptoms}, Duration: {case.request.duration_days} days)\n"
            f"- Deterministic Safety Triage: {triage.severity.value if triage else 'N/A'} (Score: {triage.score if triage else 0}, Reason: {triage.reason if triage else 'N/A'})\n"
            f"- Specialist: {assessment.specialty if assessment else 'General Medicine'}\n"
            f"- Clinical Impression: {assessment.primary_impression if assessment else 'Pending'}\n"
            f"- Differential Diagnoses: {assessment.differential_diagnoses if assessment else []}\n"
            f"- Key Recommended Actions: {assessment.recommended_actions if assessment else []}\n"
            f"- Literature Citations: {[c.get('title') for c in citations]}\n"
            f"Provide a clear, professional structured clinical summary explicitly acknowledging Patient EHR Context, Current Presentation, Safety Triage, Specialist Assessment, and Evidence."
        )
        return llm_client.generate(prompt)

    def _generate_template(self, case: CaseContext) -> str:
        triage = case.triage_result
        severity = triage.severity.value if triage else "UNKNOWN"
        assessment = case.assessment

        header = f"CLINICAL REFERRAL & ESCALATION SUMMARY\n{'=' * 45}\n"

        # Section 0: Patient EHR Context
        if case.patient_context_loaded and case.patient_id:
            cond_lines = []
            for c in case.patient_history:
                if isinstance(c, dict):
                    cond_lines.append(f"     * {c.get('description', '')} (Diagnosed: {c.get('start_date', 'N/A')})\n")
                else:
                    cond_lines.append(f"     * {c}\n")
            conditions_lines = "".join(cond_lines) or "     * No chronic conditions recorded\n"

            enc_lines = []
            for e in case.patient_encounters[:5]:
                if isinstance(e, dict):
                    enc_lines.append(f"     * {e.get('description', '')} [{e.get('class', e.get('encounter_class', 'ambulatory'))}] ({e.get('date', 'N/A')})\n")
                else:
                    enc_lines.append(f"     * {e}\n")
            encounters_lines = "".join(enc_lines) or "     * No previous encounters recorded\n"
            
            patient_section = (
                f"1. PATIENT CONTEXT (Synthea EHR Database):\n"
                f"   - Patient ID: {case.patient_id}\n"
                f"   - Name: {case.patient_name or 'N/A'}\n"
                f"   - Demographics: Age {case.patient_age if case.patient_age is not None else 'N/A'} | Gender {case.patient_gender or 'N/A'}\n"
                f"   - Recorded Conditions:\n{conditions_lines}"
                f"   - Recent Clinical Encounters:\n{encounters_lines}\n"
            )
        else:
            patient_section = (
                f"1. PATIENT CONTEXT:\n"
                f"   - Patient-specific Synthea EHR context was not provided or unavailable.\n\n"
            )

        # Section 1: Current Presentation
        presentation_section = (
            f"2. CURRENT PRESENTATION:\n"
            f"   - Chief Complaint: \"{case.raw_input}\"\n"
            f"   - Extracted Symptoms: {', '.join(case.request.symptoms) if case.request.symptoms else 'None explicitly parsed'}\n"
            f"   - Duration: {case.request.duration_days} days\n\n"
        )
        
        # Section 2: Safety & Triage Urgency
        triage_section = (
            f"3. SAFETY TRIAGE ASSESSMENT: [{severity}]\n"
            f"   - Severity Score: {triage.score if triage else 0}/100\n"
            f"   - Triage Rationale: {triage.reason if triage else 'N/A'}\n"
            f"   - Matched Red-Flag / Urgent Symptoms: {', '.join(triage.matched_symptoms) if triage else 'None'}\n\n"
        )

        if severity == SeverityLevel.EMERGENCY.value:
            emergency_alert = (
                "*** CRITICAL EMERGENCY ESCALATION ***\n"
                "Immediate medical stabilization is required. Patient exhibits high-acuity red-flag symptoms. "
                "Contact Emergency Medical Services (911) or proceed immediately to the nearest Emergency Department.\n\n"
            )
            triage_section = emergency_alert + triage_section

        # Section 3: Specialist Assessment
        if assessment:
            specialist_section = (
                f"4. SPECIALIST CLINICAL ASSESSMENT ({assessment.specialty.upper()}):\n"
                f"   - Primary Impression: {assessment.primary_impression}\n"
                f"   - Differential Diagnoses:\n" +
                "".join([f"     * {d}\n" for d in assessment.differential_diagnoses]) +
                f"   - Clinical Pathophysiology & Reasoning:\n     {assessment.clinical_reasoning}\n\n"
                f"5. RECOMMENDED DIAGNOSTIC & MANAGEMENT ACTIONS:\n" +
                "".join([f"   [{idx + 1}] {action}\n" for idx, action in enumerate(assessment.recommended_actions)]) + "\n"
            )
        else:
            specialist_section = "4. SPECIALIST ASSESSMENT: Short-circuited directly to emergency escalation.\n\n"

        # Section 4: Evidence & Citations
        if case.citations:
            evidence_section = "6. EVIDENCE-BASED LITERATURE CITATIONS (NCBI PubMed RAG):\n"
            for cit in case.citations:
                pmid_str = f" [PMID: {cit.get('pmid')}]" if cit.get('pmid') else ""
                evidence_section += f"   - {cit.get('title')}{pmid_str}\n     URL: {cit.get('url')}\n"
        else:
            evidence_section = "6. EVIDENCE-BASED CITATIONS: Direct emergency escalation; evidence retrieval deferred."

        disclaimer = (
            "\n\nNOTICE: This advisory summary is generated by the Vaidya Multi-Agent Decision Support System "
            "for informational and triage screening purposes. Deterministic safety rules strictly govern severity scoring."
        )

        return header + patient_section + presentation_section + triage_section + specialist_section + evidence_section + disclaimer
