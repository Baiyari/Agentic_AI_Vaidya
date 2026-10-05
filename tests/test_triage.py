import pytest
from core.models import TriageRequest, SeverityLevel
from core.triage import assess_severity, check_red_flags, RED_FLAG_COMBINATIONS
from core.exceptions import TriageValidationError
from agents.intake_agent import IntakeAgent


@pytest.mark.parametrize("combo,expected_reason", RED_FLAG_COMBINATIONS)
def test_all_red_flag_combinations_trigger_emergency(combo, expected_reason):
    """Verifies that every single red-flag combination triggers an immediate EMERGENCY."""
    req = TriageRequest(symptoms=list(combo), age=35, duration_days=1.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY, f"Failed for combo {combo}"
    assert res.score == 100
    for symptom in combo:
        assert symptom in res.matched_symptoms


def test_chest_pain_2_hours_age_60_triggers_emergency():
    """Verifies that chest pain in a 60yo patient with 2 hours duration triggers EMERGENCY."""
    # Test with duration_hours=2.0
    req = TriageRequest(symptoms=["chest_pain"], age=60, duration_days=0.083, duration_hours=2.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY
    assert res.score == 100
    assert "chest_pain" in res.matched_symptoms
    assert "Acute chest pain" in res.reason or "Acute Coronary Syndrome" in res.reason


def test_stroke_symptoms_trigger_emergency():
    """Verifies that individual stroke symptoms trigger EMERGENCY."""
    stroke_symptoms = ["slurred_speech", "facial_drooping", "weakness_one_side", "sudden_numbness"]
    for sym in stroke_symptoms:
        req = TriageRequest(symptoms=[sym], age=65, duration_days=0.1, duration_hours=2.0)
        res = assess_severity(req)
        assert res.severity == SeverityLevel.EMERGENCY, f"Failed for {sym}"
        assert res.score == 100
        assert sym in res.matched_symptoms


def test_severe_breathlessness_triggers_emergency_or_high():
    """Verifies that severe breathing difficulty triggers EMERGENCY or HIGH."""
    # Stridor -> Emergency
    req1 = TriageRequest(symptoms=["stridor"], age=45, duration_days=0.5)
    res1 = assess_severity(req1)
    assert res1.severity == SeverityLevel.EMERGENCY
    assert res1.score == 100

    # Difficulty breathing with facial swelling -> Emergency
    req2 = TriageRequest(symptoms=["difficulty_breathing", "swelling_face"], age=30, duration_days=0.1)
    res2 = assess_severity(req2)
    assert res2.severity == SeverityLevel.EMERGENCY

    # Difficulty breathing standalone in younger patient -> at least HIGH
    req3 = TriageRequest(symptoms=["difficulty_breathing"], age=40, duration_days=3.0)
    res3 = assess_severity(req3)
    assert res3.severity in [SeverityLevel.HIGH, SeverityLevel.EMERGENCY]
    assert res3.score >= 12


def test_mild_headache_two_days_stays_low():
    """Verifies that mild headache for two days in a 54-year-old stays LOW severity."""
    req = TriageRequest(symptoms=["headache"], age=54, duration_days=2.0, duration_hours=48.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.LOW
    assert res.score < 8
    assert "Routine care recommended" in res.reason


def test_duration_parsing_in_hours_and_sub_day():
    """Verifies natural language parsing of durations in hours, minutes, and time anchors."""
    agent = IntakeAgent()

    # "two hours" -> 2 hours, ~0.083 days (never 0 days)
    req1 = agent._parse_with_rules("I am 60 years old and have had chest pain for two hours.")
    assert req1.age == 60
    assert "chest_pain" in req1.symptoms
    assert req1.duration_hours == 2.0
    assert 0.08 <= req1.duration_days <= 0.09
    assert req1.duration_days > 0

    # "30 minutes" -> 0.5 hours, ~0.021 days
    req2 = agent._parse_with_rules("I am 45 with shortness of breath for 30 minutes.")
    assert req2.duration_hours == 0.5
    assert 0.02 <= req2.duration_days <= 0.03

    # "since this morning" -> 6.0 hours, 0.25 days
    req3 = agent._parse_with_rules("I am 50 and feel dizzy since this morning.")
    assert req3.duration_hours == 6.0
    assert req3.duration_days == 0.25

    # "for two days" -> 48 hours, 2.0 days
    req4 = agent._parse_with_rules("I am 54 years old and have had mild headache for two days.")
    assert req4.age == 54
    assert req4.duration_days == 2.0
    assert req4.duration_hours == 48.0


def test_emergency_meningitis():
    req = TriageRequest(symptoms=["fever", "stiff_neck", "confusion"], age=22, duration_days=1.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY


def test_emergency_coughing_blood():
    req = TriageRequest(symptoms=["coughing_blood"], age=45, duration_days=1.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY


def test_emergency_airway_stridor():
    req = TriageRequest(symptoms=["stridor"], age=4, duration_days=0.1)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY


def test_emergency_seizures():
    req = TriageRequest(symptoms=["seizures"], age=30, duration_days=0.1)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.EMERGENCY


def test_high_severity_score():
    # 5 symptoms (10 pts) + age > 65 (5 pts) = 15 pts -> HIGH
    req = TriageRequest(symptoms=["cough", "fever", "nausea", "dizziness", "joint_pain"], age=70, duration_days=2.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.HIGH
    assert res.score >= 15


def test_moderate_severity_score():
    # 2 symptoms (4 pts) + age 55 (2 pts) + duration > 14 (3 pts) = 9 pts -> MODERATE
    req = TriageRequest(symptoms=["cough", "fever"], age=55, duration_days=15.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.MODERATE
    assert 8 <= res.score < 15


def test_low_severity_score():
    # 1 symptom (2 pts) = 2 pts -> LOW
    req = TriageRequest(symptoms=["skin_rash"], age=30, duration_days=2.0)
    res = assess_severity(req)
    assert res.severity == SeverityLevel.LOW
    assert res.score < 8


def test_no_symptoms_raises_error():
    with pytest.raises(ValueError):
        TriageRequest(symptoms=[], age=30, duration_days=2.0)
