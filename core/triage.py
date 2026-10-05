import logging
from typing import List, Tuple

from core.models import TriageRequest, TriageResult, SeverityLevel, SpecialistSuggestion
from core.icd_lookup import get_specialist_for_symptoms
from core.exceptions import TriageValidationError

logger = logging.getLogger(__name__)

# Red flag single symptoms that instantly trigger an EMERGENCY severity
SINGLE_RED_FLAG_SYMPTOMS = {
    "severe_bleeding": "Critical hemorrhage: Severe active bleeding requires immediate emergency surgical/trauma intervention.",
    "stridor": "Critical airway compromise: Stridor indicates imminent upper airway obstruction.",
    "coughing_blood": "Massive hemoptysis / pulmonary emergency: Coughing blood mandates immediate emergency care.",
    "seizures": "Acute neurological emergency: Seizures / status epilepticus mandate urgent stabilization.",
    "slurred_speech": "Acute stroke / focal neurological deficit: Slurred speech requires immediate stroke code activation.",
    "facial_drooping": "Acute stroke sign: Facial drooping requires immediate stroke code activation.",
    "weakness_one_side": "Acute stroke sign: Unilateral weakness requires immediate stroke protocol activation.",
    "sudden_numbness": "Acute neurological deficit: Sudden focal numbness requires urgent stroke evaluation.",
    "suicidal_thoughts": "Critical psychiatric emergency: Active suicidal ideation requires immediate crisis intervention.",
    "syncope": "Sudden loss of consciousness / syncope: Requires immediate emergency hemodynamic and neuro evaluation."
}

# Red flag combinations that instantly trigger an EMERGENCY severity
RED_FLAG_COMBINATIONS = [
    ({"chest_pain", "shortness_of_breath"}, "Critical red-flag combination detected: chest pain and shortness of breath (suspected ACS / PE)."),
    ({"chest_pain", "difficulty_breathing"}, "Critical red-flag combination detected: chest pain and difficulty breathing."),
    ({"sudden_severe_headache", "vision_loss"}, "Critical red-flag combination detected: sudden severe headache and vision loss (suspected intracranial event)."),
    ({"difficulty_breathing", "swelling_face"}, "Critical red-flag combination detected: respiratory distress with facial swelling (suspected anaphylaxis)."),
    ({"fever", "stiff_neck", "confusion"}, "Critical red-flag combination detected: fever, stiff neck, and confusion (suspected bacterial meningitis)."),
    ({"fever", "stiff_neck"}, "Critical red-flag combination detected: fever and stiff neck (suspected acute meningitis)."),
    ({"dizziness", "chest_pain"}, "Critical red-flag combination detected: chest pain with dizziness (suspected cardiogenic shock/arrhythmia).")
]


def check_red_flags(request: TriageRequest) -> Tuple[bool, List[str], str]:
    """
    Checks if the triage request triggers any deterministic clinical red flags.
    
    Args:
        request: The domain TriageRequest object.
        
    Returns:
        Tuple of (is_emergency, matched_symptoms, reason_string)
    """
    symptoms_set = {s.lower().strip() for s in request.symptoms}
    
    # 1. Check multi-symptom red flag combinations first
    for combo, reason in RED_FLAG_COMBINATIONS:
        if combo.issubset(symptoms_set):
            return True, list(combo), reason

    # 2. Check single critical emergency symptoms
    for sym, reason in SINGLE_RED_FLAG_SYMPTOMS.items():
        if sym in symptoms_set:
            return True, [sym], reason

    # 3. Chest pain with age >= 50 OR acute duration in hours (<= 48 hours / < 2 days)
    if "chest_pain" in symptoms_set:
        is_acute_duration = (
            (request.duration_hours is not None and request.duration_hours <= 48) or
            request.duration_days < 2.0
        )
        if request.age >= 50 or is_acute_duration:
            reason = (
                f"Critical red-flag: Acute chest pain (age {request.age}, duration {request.duration_days}d / "
                f"{request.duration_hours if request.duration_hours else round(request.duration_days * 24, 1)}h) "
                "mandates immediate emergency cardiac evaluation (suspected Acute Coronary Syndrome / Myocardial Infarction / Aortic Dissection)."
            )
            return True, ["chest_pain"], reason
            
    return False, [], ""


def calculate_severity_score(request: TriageRequest) -> int:
    """
    Calculates a severity score based on symptoms, age, and duration.
    
    Args:
        request: The triage request domain object.
        
    Returns:
        Integer score. Higher is more severe.
    """
    score = 0
    symptoms_set = {s.lower().strip() for s in request.symptoms}
    
    # Base score on number of symptoms
    score += len(request.symptoms) * 2

    # High-risk symptom weightings
    if "chest_pain" in symptoms_set:
        score += 15
    if "difficulty_breathing" in symptoms_set or "shortness_of_breath" in symptoms_set:
        score += 15
    if "syncope" in symptoms_set:
        score += 15
        
    # Age weighting
    if request.age < 2 or request.age > 65:
        score += 5
    elif request.age > 50:
        score += 2
        
    # Duration weighting (chronic or prolonged)
    if request.duration_days > 14:
        score += 3
    elif request.duration_days > 7:
        score += 1
        
    return score


def assess_severity(request: TriageRequest) -> TriageResult:
    """
    Evaluates a triage request to determine severity, reason, and specialist.
    
    Args:
        request: A TriageRequest object.
        
    Returns:
        A TriageResult object containing the severity and mapped info.
        
    Raises:
        TriageValidationError if inputs are completely invalid.
    """
    if not request.symptoms:
        raise TriageValidationError("At least one symptom is required for triage.")
        
    is_emergency, matched_symptoms, reason = check_red_flags(request)
    specialist_sugg = get_specialist_for_symptoms(request.symptoms)
    
    if is_emergency:
        logger.warning(f"EMERGENCY detected for symptoms {matched_symptoms}. Reason: {reason}")
        return TriageResult(
            severity=SeverityLevel.EMERGENCY,
            reason=reason,
            matched_symptoms=matched_symptoms,
            score=100,
            specialist_suggestion=specialist_sugg
        )
        
    score = calculate_severity_score(request)
    
    if score >= 15:
        severity = SeverityLevel.HIGH
        reason = f"High risk score ({score}) based on presenting symptoms, clinical risk factors, and duration."
    elif score >= 8:
        severity = SeverityLevel.MODERATE
        reason = f"Moderate risk score ({score})."
    else:
        severity = SeverityLevel.LOW
        reason = f"Low risk score ({score}). Routine care recommended."
        
    logger.info(f"Triage assessed as {severity.value} with score {score}.")
    
    return TriageResult(
        severity=severity,
        reason=reason,
        matched_symptoms=request.symptoms,
        score=score,
        specialist_suggestion=specialist_sugg
    )
