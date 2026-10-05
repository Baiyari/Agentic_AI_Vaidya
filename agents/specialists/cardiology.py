from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class CardiologyAgent(BaseSpecialistAgent):
    """Specialist agent focused on cardiovascular diseases and hemodynamic stabilization."""

    def __init__(self):
        super().__init__(specialty_name="Cardiology")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age
        has_chest_pain = "chest_pain" in symptoms
        has_palpitations = "palpitations" in symptoms or "irregular_heartbeat" in symptoms
        has_edema = "peripheral_edema" in symptoms or "swollen_ankles" in symptoms
        has_sob = "shortness_of_breath" in symptoms or "shortness_of_breath_on_exertion" in symptoms

        differentials = []
        evidence_terms = []
        actions = []

        if has_chest_pain:
            primary_impression = "Suspected Acute Coronary Syndrome / Ischemic Heart Disease"
            differentials = ["Myocardial Infarction", "Unstable Angina", "Aortic Dissection", "Pericarditis", "Costochondritis"]
            actions = [
                "Immediate 12-lead Electrocardiogram (ECG)",
                "Serial high-sensitivity cardiac troponin (hs-cTn) assays",
                "Continuous cardiac rhythm monitoring",
                "Basic Metabolic Panel and Complete Blood Count"
            ]
            evidence_terms = ["acute coronary syndrome evaluation", "cardiac troponin high sensitivity triage"]
            reasoning = (
                f"Patient presenting with chest pain at age {age}. Given the high risk of myocardial ischemia, "
                f"urgent ruling out of coronary artery occlusion is mandatory. Duration of {case.request.duration_days} days "
                "warrants immediate evaluation for ongoing ischemic injury and hemodynamic instability."
            )
        elif has_edema or has_sob:
            primary_impression = "Decompensated Congestive Heart Failure / Fluid Overload"
            differentials = ["Congestive Heart Failure (NYHA Class III/IV)", "Valvular Heart Disease", "Cor Pulmonale", "Cardiomyopathy"]
            actions = [
                "Serum B-type Natriuretic Peptide (BNP or NT-proBNP)",
                "Transthoracic Echocardiogram (TTE) for ejection fraction",
                "Chest X-ray to assess pulmonary venous congestion",
                "Renal function and electrolyte panel"
            ]
            evidence_terms = ["congestive heart failure BNP echocardiography", "heart failure management"]
            reasoning = (
                f"Symptom constellation of breathlessness and peripheral swelling suggests cardiac fluid overload. "
                "Evaluating left ventricular systolic/diastolic function and neurohormonal activation is indicated."
            )
        elif has_palpitations:
            primary_impression = "Cardiac Arrhythmia / Atrial Fibrillation"
            differentials = ["Atrial Fibrillation", "Paroxysmal Supraventricular Tachycardia", "Ventricular Ectopy", "Thyrotoxicosis"]
            actions = [
                "12-lead ECG and 24-48 hour Holter ambulatory monitor",
                "Thyroid-stimulating hormone (TSH) level",
                "Serum electrolytes (potassium, magnesium)"
            ]
            evidence_terms = ["atrial fibrillation diagnosis guidelines", "cardiac arrhythmia palpitations"]
            reasoning = (
                "Patient notes palpitations and heart rhythm irregularity. Objective rhythm capture is necessary "
                "to differentiate benign supraventricular ectopy from hemodynamically compromising arrhythmias."
            )
        else:
            primary_impression = "Cardiovascular Risk Assessment & Essential Hypertension"
            differentials = ["Primary Hypertension", "Secondary Hypertension", "Dyslipidemia"]
            actions = ["Serial blood pressure monitoring", "Lipid profile", "Cardiovascular risk score calculation"]
            evidence_terms = ["hypertension cardiovascular risk guidelines"]
            reasoning = "Cardiovascular screening indicated based on reported symptoms and age-related vascular risk."

        # Check for LLM enhancement if available
        if llm_client.is_available():
            prompt = (
                f"Patient symptoms: {symptoms}, Age: {age}, Duration: {case.request.duration_days} days. "
                f"Specialist: Cardiology. Provide a concise 2-sentence clinical impression and recommended diagnostic step."
            )
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
