import logging
from typing import List, Tuple, Dict
from collections import Counter

from core.icd_lookup import SYMPTOM_MAP

logger = logging.getLogger(__name__)

# Canonical specialist agent names available in the pool
CANONICAL_SPECIALTIES = {
    "Cardiologist": "Cardiology",
    "Cardiology": "Cardiology",
    "Pulmonologist": "Pulmonology",
    "Pulmonology": "Pulmonology",
    "Neurologist": "Neurology",
    "Neurology": "Neurology",
    "Gastroenterologist": "Gastroenterology",
    "Gastroenterology": "Gastroenterology",
    "Dermatologist": "Dermatology",
    "Dermatology": "Dermatology",
    "General Practitioner": "General Medicine",
    "General Medicine": "General Medicine",
    # Mappings for other specialties to nearest primary specialist agent
    "Allergist / Immunologist": "Dermatology",
    "Rheumatologist": "General Medicine",
    "Orthopedist": "General Medicine",
    "Otolaryngologist": "Pulmonology",
    "Ophthalmologist": "Neurology",
    "Urologist": "Gastroenterology",
    "Emergency Medicine": "General Medicine"
}


class SpecialtyRouter:
    """
    Table-driven, deterministic routing agent that maps symptoms to candidate medical specialties.
    Uses the expanded symptom taxonomy to rank specialties by symptom count and clinical relevance.
    """

    def route(self, symptoms: List[str]) -> List[Tuple[str, float]]:
        """
        Ranks candidate specialties for the given symptoms.
        Returns a list of (specialty_name, confidence_score) sorted from highest to lowest.
        """
        specialty_counts: Counter = Counter()

        for s in symptoms:
            norm = s.lower().strip()
            if norm in SYMPTOM_MAP:
                raw_specialist = SYMPTOM_MAP[norm][1]
                canonical = CANONICAL_SPECIALTIES.get(raw_specialist, "General Medicine")
                specialty_counts[canonical] += 1

        if not specialty_counts:
            return [("General Medicine", 1.0)]

        total_matches = sum(specialty_counts.values())
        ranked = [
            (spec, round(count / total_matches, 2))
            for spec, count in specialty_counts.most_common()
        ]
        return ranked

    def get_primary_specialty(self, symptoms: List[str]) -> str:
        """Returns the top recommended specialist pool name."""
        ranked = self.route(symptoms)
        return ranked[0][0] if ranked else "General Medicine"
