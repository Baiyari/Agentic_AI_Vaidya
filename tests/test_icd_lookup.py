import pytest
from core.icd_lookup import (
    get_specialist_for_symptoms,
    lookup_condition_category,
    get_all_symptoms,
    SYMPTOM_MAP
)

def test_lookup_existing_symptom():
    category = lookup_condition_category("chest_pain")
    assert category == "Diseases of the circulatory system"

def test_lookup_case_insensitive():
    category = lookup_condition_category("   CHEST_PAIN ")
    assert category == "Diseases of the circulatory system"

def test_lookup_unknown_symptom():
    category = lookup_condition_category("unknown_symptom_123")
    assert category is None

def test_specialist_suggestion():
    suggestion = get_specialist_for_symptoms(["unknown_symptom", "fever"])
    assert suggestion is not None
    assert suggestion.specialist == "General Practitioner"
    assert suggestion.category == "Certain infectious or parasitic diseases"

def test_taxonomy_size():
    """Verify that the taxonomy has expanded significantly beyond the original 15 entries."""
    symptoms = get_all_symptoms()
    assert len(symptoms) >= 80, f"Expected at least 80 symptoms, found {len(symptoms)}"

@pytest.mark.parametrize("symptom,expected_specialist", [
    ("palpitations", "Cardiologist"),
    ("hypertension", "Cardiologist"),
    ("peripheral_edema", "Cardiologist"),
    ("wheezing", "Pulmonologist"),
    ("chronic_cough", "Pulmonologist"),
    ("hemoptysis", "Pulmonologist"),
    ("migraine", "Neurologist"),
    ("vertigo", "Neurologist"),
    ("tremor", "Neurologist"),
    ("slurred_speech", "Neurologist"),
    ("vomiting", "Gastroenterologist"),
    ("diarrhea", "Gastroenterologist"),
    ("jaundice", "Gastroenterologist"),
    ("melena", "Gastroenterologist"),
    ("itching", "Dermatologist"),
    ("hives", "Dermatologist"),
    ("eczema", "Dermatologist"),
    ("night_sweats", "General Practitioner"),
    ("fatigue", "General Practitioner"),
    ("knee_pain", "Orthopedist"),
    ("shoulder_pain", "Orthopedist"),
    ("morning_stiffness", "Rheumatologist"),
    ("blurred_vision", "Ophthalmologist"),
    ("hearing_loss", "Otolaryngologist"),
    ("blood_in_urine", "Urologist"),
])
def test_twenty_five_expanded_symptom_mappings(symptom, expected_specialist):
    """Verifies at least 25 new and diverse symptom mappings across clinical specialties."""
    suggestion = get_specialist_for_symptoms([symptom])
    assert suggestion is not None, f"Mapping missing for {symptom}"
    assert suggestion.specialist == expected_specialist, f"Mismatch for {symptom}: expected {expected_specialist}, got {suggestion.specialist}"
