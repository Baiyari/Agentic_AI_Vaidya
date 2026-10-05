from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class PulmonologyAgent(BaseSpecialistAgent):
    """Specialist agent focused on respiratory pathophysiology, ventilation, and airway diseases."""

    def __init__(self):
        super().__init__(specialty_name="Pulmonology")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age
        has_hemoptysis = "coughing_blood" in symptoms or "hemoptysis" in symptoms
        has_wheezing = "wheezing" in symptoms or "difficulty_breathing" in symptoms
        has_cough = "cough" in symptoms or "chronic_cough" in symptoms or "productive_cough" in symptoms
        has_stridor = "stridor" in symptoms

        if has_stridor or has_hemoptysis:
            primary_impression = "Critical Airway or Alveolar Hemorrhage / Pulmonary Embolism"
            differentials = ["Pulmonary Embolism", "Bronchogenic Carcinoma", "Upper Airway Obstruction", "Active Tuberculosis"]
            actions = [
                "Immediate airway protection and supplemental oxygen therapy",
                "CT Angiography of the Chest (PE protocol)",
                "Arterial Blood Gas (ABG) analysis",
                "Coagulation profile (PT/INR, aPTT)"
            ]
            evidence_terms = ["pulmonary embolism computed tomography angiography", "hemoptysis diagnostic evaluation"]
            reasoning = (
                "Presentation with hemoptysis or stridor represents an immediate threat to oxygenation and airway integrity. "
                "Urgent cross-sectional vascular imaging is mandatory."
            )
        elif has_wheezing:
            primary_impression = "Acute Bronchospasm / Asthma or COPD Exacerbation"
            differentials = ["Asthma Exacerbation", "COPD with Acute Lower Respiratory Infection", "Bronchitis", "Hypersensitivity Pneumonitis"]
            actions = [
                "Spirometry / Peak Expiratory Flow measurement",
                "Inhaled short-acting beta-agonist (SABA) and anticholinergic trial",
                "Chest Radiography to exclude focal pneumonia or pneumothorax",
                "Pulse oximetry monitoring"
            ]
            evidence_terms = ["asthma exacerbation management guidelines", "chronic obstructive pulmonary disease bronchodilators"]
            reasoning = (
                f"Auscultatory and patient-reported wheezing with respiratory effort indicates airway hyperresponsiveness "
                f"or small-airway obstruction in a {age}-year-old patient."
            )
        else:
            primary_impression = "Acute Respiratory Infection / Bronchitis"
            differentials = ["Acute Bronchitis", "Community-Acquired Pneumonia", "Post-nasal drip cough syndrome", "Viral URI"]
            actions = [
                "Standard posteroanterior and lateral Chest X-ray",
                "Sputum culture and viral respiratory multiplex PCR panel",
                "Symptomatic cough suppression and hydration"
            ]
            evidence_terms = ["community acquired pneumonia diagnosis", "acute bronchitis guidelines"]
            reasoning = (
                f"Respiratory symptoms of {case.request.duration_days} days duration indicate inflammatory involvement "
                "of the tracheobronchial tree. Primary objective is distinguishing uncomplicated bronchitis from consolidation."
            )

        if llm_client.is_available():
            prompt = f"Patient symptoms: {symptoms}, Age: {age}. Pulmonology evaluation: provide 2-sentence clinical assessment."
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
