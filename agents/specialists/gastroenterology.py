from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class GastroenterologyAgent(BaseSpecialistAgent):
    """Specialist agent focused on luminal GI, hepatic, and pancreatobiliary systems."""

    def __init__(self):
        super().__init__(specialty_name="Gastroenterology")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age

        has_gi_bleed = "melena" in symptoms or "blood_in_stool" in symptoms or "rectal_bleeding" in symptoms
        has_jaundice = "jaundice" in symptoms or "yellowing_eyes" in symptoms
        has_abd_pain = "abdominal_pain" in symptoms or "stomach_cramps" in symptoms
        has_gerd = "heartburn" in symptoms or "acid_reflux" in symptoms

        if has_gi_bleed:
            primary_impression = "Gastrointestinal Hemorrhage (Upper vs Lower GI Bleed)"
            differentials = ["Peptic Ulcer Disease", "Esophageal Varices", "Diverticular Bleeding", "Colorectal Malignancy", "Arteriovenous Malformation"]
            actions = [
                "Two large-bore IV lines and fluid resuscitation",
                "Type and cross-match for packed red blood cells",
                "Emergent Esophagogastroduodenoscopy (EGD) / Colonoscopy",
                "Intravenous Proton Pump Inhibitor (PPI) infusion"
            ]
            evidence_terms = ["upper gastrointestinal bleeding endoscopy guidelines", "lower GI hemorrhage diagnosis"]
            reasoning = (
                "Intraluminal blood loss indicates vascular or mucosal disruption. Emergent endoscopic intervention "
                "is indicated to localize the bleed and deliver endoscopic hemostasis."
            )
        elif has_jaundice:
            primary_impression = "Hepatobiliary Dysfunction / Obstructive Jaundice"
            differentials = ["Choledocholithiasis", "Acute Hepatitis", "Biliary Tract Obstruction", "Decompensated Cirrhosis"]
            actions = [
                "Comprehensive Hepatic Function Panel (Total/Direct Bilirubin, ALT, AST, ALP, GGT)",
                "Right Upper Quadrant (RUQ) Abdominal Ultrasound",
                "Magnetic Resonance Cholangiopancreatography (MRCP)",
                "Serum lipase and amylase"
            ]
            evidence_terms = ["jaundice evaluation ultrasound MRCP", "choledocholithiasis diagnostic guidelines"]
            reasoning = "Hyperbilirubinemia requires rapid differentiation between intrahepatic parenchymal disease and extrahepatic biliary obstruction."
        elif has_abd_pain:
            primary_impression = "Acute Abdominal Pain Syndrome"
            differentials = ["Acute Appendicitis", "Acute Cholecystitis", "Peptic Ulcer Disease", "Gastroenteritis"]
            actions = [
                "Serial abdominal examinations",
                "Abdominal and Pelvic CT with IV contrast",
                "Complete Blood Count with differential and serum lactate",
                "Lipase and urinalysis"
            ]
            evidence_terms = ["acute abdominal pain diagnostic approach", "appendicitis diagnosis CT"]
            reasoning = (
                f"Abdominal pain in patient age {age} with {case.request.duration_days} days duration. "
                "Cross-sectional imaging is appropriate to rule out surgical abdomen."
            )
        elif has_gerd:
            primary_impression = "Gastroesophageal Reflux Disease (GERD)"
            differentials = ["GERD / Reflux Esophagitis", "Eosinophilic Esophagitis", "Functional Dyspepsia"]
            actions = [
                "Trial of once-daily oral Proton Pump Inhibitor (PPI) for 8 weeks",
                "Dietary modification (avoid late meals, caffeine, acidic foods)",
                "Consider EGD if alarm features (dysphagia, weight loss) present"
            ]
            evidence_terms = ["gastroesophageal reflux disease management guidelines", "GERD proton pump inhibitors"]
            reasoning = "Retrosternal pyrosis is characteristic of acid exposure to esophageal squamous epithelium."
        else:
            primary_impression = "Gastrointestinal Dysmotility / Irritable Bowel Syndrome"
            differentials = ["Irritable Bowel Syndrome (IBS)", "Dietary Intolerance", "Post-infectious Dysmotility"]
            actions = ["Stool testing for infection and fecal calprotectin", "Celiac disease serology", "Dietary symptom diary"]
            evidence_terms = ["irritable bowel syndrome diagnostic criteria Rome IV"]
            reasoning = "Chronic or recurrent GI changes without red flags are consistent with functional or inflammatory gut symptoms."

        if llm_client.is_available():
            prompt = f"Patient symptoms: {symptoms}, Age: {age}. Gastroenterology evaluation: provide 2-sentence clinical assessment."
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
