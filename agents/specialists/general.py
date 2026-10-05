from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class GeneralMedicineAgent(BaseSpecialistAgent):
    """Specialist agent focused on general internal medicine, constitutional signs, and multi-system care."""

    def __init__(self):
        super().__init__(specialty_name="General Medicine")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age

        has_fever = "fever" in symptoms or "chills" in symptoms or "night_sweats" in symptoms
        has_fatigue = "fatigue" in symptoms or "malaise" in symptoms or "generalized_weakness" in symptoms
        has_joint = "joint_pain" in symptoms or "back_pain" in symptoms or "knee_pain" in symptoms

        if has_fever:
            primary_impression = "Acute Systemic Febrile Syndrome / Viral vs Bacterial Illness"
            differentials = ["Viral Syndrome / Influenza", "Urinary Tract Infection", "Occult Bacterial Infection", "Mononucleosis"]
            actions = [
                "Complete Blood Count with manual differential",
                "C-reactive protein (CRP) and Erythrocyte Sedimentation Rate (ESR)",
                "Urinalysis with microscopic examination and culture",
                "Temperature charting and oral rehydration therapy"
            ]
            evidence_terms = ["fever of unknown origin diagnostic approach", "adult febrile illness guidelines"]
            reasoning = (
                f"Elevated body temperature in a {age}-year-old with {case.request.duration_days} days of symptoms "
                "suggests an active immunological or inflammatory response to infectious pathogen."
            )
        elif has_joint:
            primary_impression = "Musculoskeletal Arthralgia / Mechanical vs Inflammatory Arthritis"
            differentials = ["Osteoarthritis", "Degenerative Disc Disease", "Early Rheumatoid Arthritis", "Soft-tissue strain"]
            actions = [
                "Targeted plain radiograph of affected joint(s)",
                "Trial of oral NSAIDs or acetaminophen with stomach protection",
                "Serum rheumatoid factor (RF) and anti-CCP antibodies if morning stiffness present",
                "Physical therapy referral"
            ]
            evidence_terms = ["osteoarthritis diagnosis treatment guidelines", "inflammatory arthritis differential"]
            reasoning = "Localized musculoskeletal pain requires differentiation between mechanical degenerative wear and systemic autoimmune synovitis."
        elif has_fatigue:
            primary_impression = "Chronic Fatigue & Constitutional Symptom Complex"
            differentials = ["Iron Deficiency Anemia", "Hypothyroidism", "Sleep Apnea", "Depressive Disorder", "Vitamin D/B12 deficiency"]
            actions = [
                "Complete Blood Count and serum ferritin",
                "Comprehensive Metabolic Panel and Thyroid Stimulating Hormone (TSH)",
                "HbA1c and Vitamin B12 / 25-OH Vitamin D levels"
            ]
            evidence_terms = ["evaluation of fatigue in adults", "unexplained fatigue laboratory testing"]
            reasoning = f"Persistent fatigue in patient age {age} warrants comprehensive metabolic, hematologic, and endocrine screening."
        else:
            primary_impression = "Undifferentiated Medical Presentation / Primary Care Evaluation"
            differentials = ["Functional Somatic Syndrome", "Mild Viral Illness", "Early-stage systemic condition"]
            actions = [
                "Comprehensive clinical history and vital signs physical exam",
                "Baseline outpatient blood and urine laboratory workup",
                "Primary care follow-up within 1 to 2 weeks"
            ]
            evidence_terms = ["primary care diagnostic reasoning adults"]
            reasoning = "General internal medicine assessment indicated to establish a baseline diagnostic timeline."

        if llm_client.is_available():
            prompt = f"Patient symptoms: {symptoms}, Age: {age}. General Medicine evaluation: provide 2-sentence clinical assessment."
            llm_text = llm_client.generate(prompt)
            if llm_text:
                reasoning = f"{llm_text}\n\n[Deterministic Rationale]: {reasoning}"

        return self._build_template_assessment(
            case=case,
            primary_impression=primary_impression,
            differentials=differentials,
            reasoning=reasoning,
            recommended_actions=actions,
            evidence_terms=evidence_terms
        )
