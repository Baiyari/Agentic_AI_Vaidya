import os
import json
import logging
from typing import Optional, Dict, Tuple, Any
from core.models import SpecialistSuggestion

logger = logging.getLogger(__name__)

# Fallback dictionary matching the original base taxonomy
_DEFAULT_SYMPTOM_MAP: Dict[str, Tuple[str, str]] = {
    "chest_pain": ("Diseases of the circulatory system", "Cardiologist"),
    "shortness_of_breath": ("Diseases of the respiratory system", "Pulmonologist"),
    "severe_bleeding": ("Injury, poisoning or certain other consequences of external causes", "Emergency Medicine"),
    "sudden_severe_headache": ("Diseases of the nervous system", "Neurologist"),
    "vision_loss": ("Diseases of the eye and adnexa", "Ophthalmologist"),
    "difficulty_breathing": ("Diseases of the respiratory system", "Pulmonologist"),
    "swelling_face": ("Diseases of the skin and subcutaneous tissue", "Allergist / Immunologist"),
    "fever": ("Certain infectious or parasitic diseases", "General Practitioner"),
    "cough": ("Diseases of the respiratory system", "General Practitioner"),
    "nausea": ("Diseases of the digestive system", "Gastroenterologist"),
    "abdominal_pain": ("Diseases of the digestive system", "Gastroenterologist"),
    "joint_pain": ("Diseases of the musculoskeletal system and connective tissue", "Rheumatologist"),
    "back_pain": ("Diseases of the musculoskeletal system and connective tissue", "Orthopedist"),
    "skin_rash": ("Diseases of the skin and subcutaneous tissue", "Dermatologist"),
    "dizziness": ("Diseases of the nervous system", "Neurologist"),
}

def _load_symptom_taxonomy() -> Tuple[Dict[str, Tuple[str, str]], Dict[str, Dict[str, Any]]]:
    """
    Loads data-driven symptom-to-specialty taxonomy from data/seed/symptom_specialty_map.json.
    Falls back gracefully to _DEFAULT_SYMPTOM_MAP if file is missing or invalid.
    """
    seed_path = os.path.join(os.path.dirname(__file__), "..", "data", "seed", "symptom_specialty_map.json")
    symptom_map: Dict[str, Tuple[str, str]] = dict(_DEFAULT_SYMPTOM_MAP)
    full_metadata: Dict[str, Dict[str, Any]] = {}

    if os.path.exists(seed_path):
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for symptom_key, info in data.items():
                    key = symptom_key.lower().strip()
                    category = info.get("category", "General symptoms and signs")
                    specialist = info.get("specialist", "General Practitioner")
                    symptom_map[key] = (category, specialist)
                    full_metadata[key] = info
            logger.info(f"Loaded {len(symptom_map)} symptom mappings from {seed_path}")
        except Exception as e:
            logger.warning(f"Could not load seed taxonomy from {seed_path}: {e}. Using fallback map.")
    else:
        logger.warning(f"Seed taxonomy not found at {seed_path}. Using fallback map.")

    return symptom_map, full_metadata

# Global in-memory lookup maps populated at module import
SYMPTOM_MAP, SYMPTOM_METADATA = _load_symptom_taxonomy()


def get_specialist_for_symptoms(symptoms: list[str]) -> Optional[SpecialistSuggestion]:
    """
    Returns a specialist suggestion based on the most severe or first matched symptom.
    
    Args:
        symptoms: A list of symptom strings.
        
    Returns:
        SpecialistSuggestion object if a match is found, otherwise None.
    """
    for symptom in symptoms:
        normalized_symptom = symptom.lower().strip()
        if normalized_symptom in SYMPTOM_MAP:
            category, specialist = SYMPTOM_MAP[normalized_symptom]
            return SpecialistSuggestion(category=category, specialist=specialist)
            
    return None


def lookup_condition_category(symptom: str) -> Optional[str]:
    """
    Looks up the ICD-style category for a single symptom.
    
    Args:
        symptom: The symptom to lookup.
        
    Returns:
        The category string or None if not found.
    """
    normalized_symptom = symptom.lower().strip()
    if normalized_symptom in SYMPTOM_MAP:
        return SYMPTOM_MAP[normalized_symptom][0]
    return None


def get_all_symptoms() -> list[str]:
    """Returns a list of all recognized normalized symptoms in the taxonomy."""
    return sorted(list(SYMPTOM_MAP.keys()))
