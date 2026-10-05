import pytest
from core.models import TriageRequest, TriageResult, SeverityLevel
from agents.base import CaseContext
from agents.specialists.cardiology import CardiologyAgent
from agents.specialists.pulmonology import PulmonologyAgent
from agents.specialists.neurology import NeurologyAgent
from agents.specialists.gastroenterology import GastroenterologyAgent
from agents.specialists.dermatology import DermatologyAgent
from agents.specialists.general import GeneralMedicineAgent


def test_cardiology_agent_chest_pain():
    agent = CardiologyAgent()
    req = TriageRequest(symptoms=["chest_pain"], age=58, duration_days=1)
    case = CaseContext(raw_input="Chest pain", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "Cardiology"
    assert "Coronary" in assessment.primary_impression or "Ischemic" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 3
    assert len(assessment.recommended_actions) >= 2
    assert len(assessment.key_evidence_terms) >= 1


def test_pulmonology_agent_wheezing():
    agent = PulmonologyAgent()
    req = TriageRequest(symptoms=["wheezing", "difficulty_breathing"], age=45, duration_days=3)
    case = CaseContext(raw_input="Wheezing", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "Pulmonology"
    assert "Asthma" in assessment.primary_impression or "Bronchospasm" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 2
    assert len(assessment.recommended_actions) >= 2


def test_neurology_agent_migraine():
    agent = NeurologyAgent()
    req = TriageRequest(symptoms=["migraine", "headache"], age=32, duration_days=2)
    case = CaseContext(raw_input="Headache", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "Neurology"
    assert "Headache" in assessment.primary_impression or "Migraine" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 2


def test_gastroenterology_agent_jaundice():
    agent = GastroenterologyAgent()
    req = TriageRequest(symptoms=["jaundice", "abdominal_pain"], age=50, duration_days=4)
    case = CaseContext(raw_input="Jaundice and belly pain", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "Gastroenterology"
    assert "Hepatobiliary" in assessment.primary_impression or "Jaundice" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 2


def test_dermatology_agent_rash():
    agent = DermatologyAgent()
    req = TriageRequest(symptoms=["skin_rash", "itching"], age=28, duration_days=5)
    case = CaseContext(raw_input="Itchy skin rash", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "Dermatology"
    assert "Dermatitis" in assessment.primary_impression or "Eczematous" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 2


def test_general_medicine_agent_fever():
    agent = GeneralMedicineAgent()
    req = TriageRequest(symptoms=["fever", "chills", "fatigue"], age=40, duration_days=3)
    case = CaseContext(raw_input="Fever and chills", request=req)
    assessment = agent.assess(case)

    assert assessment.specialty == "General Medicine"
    assert "Febrile" in assessment.primary_impression or "Infection" in assessment.primary_impression or "Viral" in assessment.primary_impression
    assert len(assessment.differential_diagnoses) >= 2
