from typing import List
from agents.base import BaseSpecialistAgent, CaseContext, SpecialistAssessment
from agents.llm_client import llm_client


class NeurologyAgent(BaseSpecialistAgent):
    """Specialist agent focused on central and peripheral nervous system disorders."""

    def __init__(self):
        super().__init__(specialty_name="Neurology")

    def assess(self, case: CaseContext) -> SpecialistAssessment:
        symptoms = [s.lower() for s in case.request.symptoms]
        age = case.request.age

        is_focal_deficit = "slurred_speech" in symptoms or "facial_drooping" in symptoms or "weakness_one_side" in symptoms
        is_thunderclap = "sudden_severe_headache" in symptoms
        is_seizure = "seizures" in symptoms
        is_meningismus = "stiff_neck" in symptoms and ("fever" in symptoms or "confusion" in symptoms)
        is_vertigo = "dizziness" in symptoms or "vertigo" in symptoms or "loss_of_balance" in symptoms

        if is_focal_deficit or is_thunderclap:
            primary_impression = "Acute Cerebrovascular Event / Stroke or Subarachnoid Hemorrhage"
            differentials = ["Acute Ischemic Stroke", "Subarachnoid Hemorrhage", "Intracerebral Hemorrhage", "Transient Ischemic Attack"]
            actions = [
                "Emergent Non-contrast Head CT with CT Angiography (Brain and Neck)",
                "NIH Stroke Scale (NIHSS) scoring",
                "Blood glucose check immediately",
                "Evaluation for intravenous thrombolysis or endovascular thrombectomy window"
            ]
            evidence_terms = ["acute ischemic stroke thrombolysis guidelines", "subarachnoid hemorrhage emergency diagnosis"]
            reasoning = (
                "Hyperacute focal neurological signs or thunderclap cephalea indicate an urgent neurovascular catastrophe. "
                "Time-critical neuroimaging is mandatory to guide reperfusion or surgical intervention."
            )
        elif is_meningismus:
            primary_impression = "Acute Meningitis / Central Nervous System Infection"
            differentials = ["Bacterial Meningitis", "Viral Encephalitis", "Subacute Meningoencephalitis"]
            actions = [
                "Immediate blood cultures followed by empiric broad-spectrum antibiotics and dexamethasone",
                "Head CT prior to lumbar puncture if altered mental status present",
                "Diagnostic Lumbar Puncture for CSF cell count, protein, glucose, and PCR"
            ]
            evidence_terms = ["bacterial meningitis management lumbar puncture", "acute encephalitis diagnosis"]
            reasoning = (
                "Fever coupled with nuchal rigidity and altered sensorium constitutes a classic triad for CNS infection. "
                "Immediate antimicrobial coverage is paramount to avoid mortality and permanent neurological sequelae."
            )
        elif is_seizure:
            primary_impression = "New-Onset Seizure Disorder / Epilepsy"
            differentials = ["First Unprovoked Seizure", "Metabolic Seizure", "Structural CNS Lesion", "Alcohol Withdrawal"]
            actions = [
                "Routine Electroencephalogram (EEG)",
                "Brain MRI with and without contrast",
                "Serum electrolyte panel (sodium, calcium, magnesium)",
                "Toxicology screening"
            ]
            evidence_terms = ["new onset seizure evaluation adults", "epilepsy diagnostic protocol"]
            reasoning = "Paroxysmal cerebral discharge requires EEG localization and structural cranial neuroimaging."
        elif is_vertigo:
            primary_impression = "Vestibular Syndrome / Benign Paroxysmal Positional Vertigo"
            differentials = ["BPPV", "Vestibular Neuritis", "Meniere's Disease", "Posterior Circulation Stroke"]
            actions = [
                "Dix-Hallpike diagnostic maneuver and HINTS examination",
                "Epley canalith repositioning if BPPV confirmed",
                "MRI Brain with diffusion-weighted imaging if central signs detected"
            ]
            evidence_terms = ["benign paroxysmal positional vertigo epley maneuver", "vestibular neuritis HINTS exam"]
            reasoning = (
                "Episodic imbalance or vertigo requires clinical differentiation between peripheral inner-ear canalithiasis "
                "and central brainstem/cerebellar etiology via HINTS testing."
            )
        else:
            primary_impression = "Primary Headache Syndrome / Migraine"
            differentials = ["Migraine with or without aura", "Tension-type Headache", "Cluster Headache"]
            actions = ["Headache diary monitoring", "Trial of oral triptan therapy", "Identify environmental and lifestyle triggers"]
            evidence_terms = ["migraine diagnosis and preventive treatment guidelines"]
            reasoning = f"Episodic cephalea in patient of age {age} consistent with primary neurovascular headache disorder."

        if llm_client.is_available():
            prompt = f"Patient symptoms: {symptoms}, Age: {age}. Neurology evaluation: provide 2-sentence clinical assessment."
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
