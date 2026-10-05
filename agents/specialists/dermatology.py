from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class DermatologyAgent(BaseSpecialistAgent):
    """Specialist agent focused on cutaneous pathology, immunodermatology, and rash morphology."""

    def __init__(self):
        super().__init__(specialty_name="Dermatology")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age

        has_angioedema = "swelling_face" in symptoms or "facial_swelling" in symptoms
        has_urticaria = "hives" in symptoms or "urticaria" in symptoms
        has_rash = "skin_rash" in symptoms or "itching" in symptoms or "pruritus" in symptoms or "eczema" in symptoms
        has_lesion = "skin_lesion" in symptoms or "mole_changes" in symptoms

        if has_angioedema:
            primary_impression = "Acute Angioedema / Anaphylactoid Cutaneous Reaction"
            differentials = ["IgE-mediated Anaphylaxis", "ACE-inhibitor Induced Angioedema", "Hereditary Angioedema", "Contact Dermatitis"]
            actions = [
                "Immediate airway assessment for stridor or laryngeal edema",
                "Intramuscular Epinephrine if any respiratory or hypotensive symptoms",
                "H1 and H2 antihistamines plus systemic corticosteroids",
                "Continuous telemetry and oxygen saturation monitoring"
            ]
            evidence_terms = ["angioedema emergency management guidelines", "anaphylaxis epinephrine treatment"]
            reasoning = (
                "Facial and mucosal soft-tissue extravasation carries acute risk of fatal upper airway compromise. "
                "Aggressive stabilization and anti-mediator therapy is priority."
            )
        elif has_lesion:
            primary_impression = "Suspicious Cutaneous Lesion / Melanocytic Neoplasm Evaluation"
            differentials = ["Malignant Melanoma", "Basal Cell Carcinoma", "Squamous Cell Carcinoma", "Dysplastic Nevus", "Seborrheic Keratosis"]
            actions = [
                "Dermoscopic examination utilizing the ABCDE criteria",
                "Complete full-body cutaneous examination",
                "Excisional punch or saucerization biopsy with 1-2 mm margins for histopathology"
            ]
            evidence_terms = ["melanoma dermoscopy ABCDE criteria biopsy", "cutaneous malignancy diagnosis"]
            reasoning = "Changes in cutaneous architecture, pigmentation, or symmetry necessitate dermoscopy and histopathologic confirmation."
        elif has_urticaria:
            primary_impression = "Acute Urticaria / Histamine-Mediated Wheals"
            differentials = ["Acute Urticaria (viral or idiopathic)", "Drug-induced Eruption", "Contact Urticaria"]
            actions = [
                "Second-generation non-sedating oral H1-antihistamines (e.g. cetirizine, fexofenadine)",
                "Review recent medications, antibiotics, and food ingestions",
                "Cold compress and avoidance of hot water and topical irritants"
            ]
            evidence_terms = ["acute urticaria diagnosis and treatment guidelines", "antihistamines urticaria"]
            reasoning = "Transient, pruritic, erythematous edematous wheals represent cutaneous mast-cell degranulation."
        else:
            primary_impression = "Eczematous Dermatitis / Atopic or Contact Eczema"
            differentials = ["Atopic Dermatitis", "Allergic Contact Dermatitis", "Nummular Eczema", "Psoriasis Vulgaris"]
            actions = [
                "Topical corticosteroid ointment (mid-potency for body, low-potency for face)",
                "Frequent liberal application of ceramide-rich barrier emollient",
                "Avoid harsh soaps and fragrance additives",
                "Patch testing if allergic contact allergy suspected"
            ]
            evidence_terms = ["atopic dermatitis topical corticosteroids guidelines", "eczema skin barrier repair"]
            reasoning = f"Pruritic erythematous cutaneous eruption in patient age {age} consistent with epidermal barrier breakdown."

        if llm_client.is_available():
            prompt = f"Patient symptoms: {symptoms}, Age: {age}. Dermatology evaluation: provide 2-sentence clinical assessment."
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
