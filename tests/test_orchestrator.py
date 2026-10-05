from unittest.mock import patch, MagicMock
from agents.orchestrator import MultiAgentOrchestrator
from data.models import TriageRecord, AgentTrace, EvidenceCitation
from core.models import SeverityLevel


def test_orchestrator_emergency_short_circuit(db_session):
    orchestrator = MultiAgentOrchestrator()
    orchestrator.evidence_agent.delay = 0.0

    raw_text = "I am a 62 year old male with sudden crushing chest pain and shortness of breath since 2 hours ago."
    record, ctx = orchestrator.process_case(raw_text=raw_text, session=db_session)

    assert record.id is not None
    assert record.severity == SeverityLevel.EMERGENCY.value
    assert record.score == 100
    assert "chest_pain" in ctx.request.symptoms
    assert "shortness_of_breath" in ctx.request.symptoms

    # Verify AgentTraces recorded
    traces = db_session.query(AgentTrace).filter(AgentTrace.case_id == record.id).order_by(AgentTrace.id).all()
    agent_names = [t.agent_name for t in traces]

    assert "Intake Agent" in agent_names
    assert "Safety Triage Agent" in agent_names
    assert "Emergency Escalation Agent" in agent_names
    assert "Explainability Agent" in agent_names

    # Crucial: verify that non-emergency specialist routing was bypassed
    for name in agent_names:
        assert "Specialty Router" not in name
        assert "Evidence Retrieval" not in name

    assert "CRITICAL EMERGENCY ESCALATION" in record.narrative_summary


def test_orchestrator_non_emergency_full_pipeline(db_session):
    orchestrator = MultiAgentOrchestrator()
    orchestrator.evidence_agent.delay = 0.0

    mock_esearch = {"esearchresult": {"idlist": ["99990001"]}}
    mock_esummary = {"result": {"99990001": {"title": "Topical Corticosteroid Management for Eczematous Dermatitis"}}}

    with patch("requests.get") as mock_get:
        r1 = MagicMock(status_code=200)
        r1.json.return_value = mock_esearch
        r2 = MagicMock(status_code=200)
        r2.json.return_value = mock_esummary
        mock_get.side_effect = [r1, r2]

        raw_text = "I'm 26 years old and I've had an itchy red skin rash on both arms for the past 5 days."
        record, ctx = orchestrator.process_case(raw_text=raw_text, session=db_session)

        assert record.id is not None
        assert record.severity in [SeverityLevel.LOW.value, SeverityLevel.MODERATE.value]
        assert record.specialist == "Dermatology"
        assert "skin_rash" in ctx.request.symptoms
        assert ctx.request.age == 26
        assert ctx.request.duration_days == 5

        # Verify full end-to-end AgentTrace chain
        traces = db_session.query(AgentTrace).filter(AgentTrace.case_id == record.id).order_by(AgentTrace.id).all()
        agent_names = [t.agent_name for t in traces]

        assert "Intake Agent" in agent_names
        assert "Safety Triage Agent" in agent_names
        assert "Specialty Router Agent" in agent_names
        assert "Dermatology Specialist Agent" in agent_names
        assert "Evidence Retrieval Agent" in agent_names
        assert "Explainability Agent" in agent_names

        # Verify evidence citations attached
        citations = db_session.query(EvidenceCitation).filter(EvidenceCitation.case_id == record.id).all()
        assert len(citations) >= 1
        assert "Dermatitis" in citations[0].title


def test_orchestrator_synthea_patient_context(db_session):
    orchestrator = MultiAgentOrchestrator()
    orchestrator.evidence_agent.delay = 0.0

    # Ensure a patient exists in db_session
    from data.models import Patient, Condition, Encounter
    patient = db_session.query(Patient).first()
    if not patient:
        # Create a test Synthea patient in session if running in clean memory
        patient = Patient(
            id="test-synthea-001",
            birthdate="1970-05-15",
            first_name="Jane",
            last_name="Doe",
            gender="F",
            city="Boston",
            state="MA"
        )
        db_session.add(patient)
        cond = Condition(
            patient_id="test-synthea-001",
            code="38341003",
            description="Hypertension",
            start_date="2015-01-10"
        )
        enc = Encounter(
            id="enc-001",
            patient_id="test-synthea-001",
            date="2023-08-10",
            code="185349003",
            description="Encounter for check up",
            encounter_class="ambulatory"
        )
        db_session.add_all([cond, enc])
        db_session.flush()

    raw_text = "I have had a worsening dry cough and mild shortness of breath for 3 days."
    record, ctx = orchestrator.process_case(
        raw_text=raw_text,
        session=db_session,
        patient_id=patient.id
    )

    assert record.id is not None
    assert ctx.patient_context_loaded is True
    assert ctx.patient_id == patient.id
    assert ctx.patient_gender == patient.gender
    assert ctx.patient_age is not None
    assert len(ctx.patient_history) >= 1
    assert "PATIENT CONTEXT (Synthea EHR Database)" in record.narrative_summary
    assert patient.id in record.narrative_summary

    # Check AgentTrace includes Synthea EHR Agent
    traces = db_session.query(AgentTrace).filter(AgentTrace.case_id == record.id).all()
    agent_names = [t.agent_name for t in traces]
    assert "Synthea EHR Agent" in agent_names


def test_orchestrator_invalid_patient_id(db_session):
    orchestrator = MultiAgentOrchestrator()
    orchestrator.evidence_agent.delay = 0.0

    raw_text = "I have a mild sore throat for 1 day."
    record, ctx = orchestrator.process_case(
        raw_text=raw_text,
        session=db_session,
        patient_id="invalid-demo-patient"
    )

    assert record.id is not None
    assert ctx.patient_context_loaded is False
    assert ctx.patient_id == "invalid-demo-patient"
    assert "Patient-specific Synthea EHR context was not provided or unavailable" in record.narrative_summary
