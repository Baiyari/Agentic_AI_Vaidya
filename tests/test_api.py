import json
from unittest.mock import patch, MagicMock


def test_health_check(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.json.get("status") == "ok"


def test_triage_api_success(client):
    payload = {
        "symptoms": ["chest_pain", "shortness_of_breath"],
        "age": 45,
        "duration_days": 1
    }
    resp = client.post('/api/triage', json=payload)
    assert resp.status_code == 200
    data = resp.json
    assert data["severity"] == "EMERGENCY"
    assert "id" in data
    
    # Test GET endpoint
    record_id = data["id"]
    get_resp = client.get(f'/api/triage/{record_id}')
    assert get_resp.status_code == 200
    get_data = get_resp.json
    assert get_data["severity"] == "EMERGENCY"
    assert "chest_pain" in get_data["symptoms"]


def test_triage_api_invalid_payload(client):
    payload = {
        "symptoms": [],  # Invalid, min_length 1
        "age": 45,
        "duration_days": 1
    }
    resp = client.post('/api/triage', json=payload)
    assert resp.status_code == 400
    assert "error" in resp.json


def test_cases_post_and_get_detail(client):
    mock_esearch = {"esearchresult": {"idlist": ["55555555"]}}
    mock_esummary = {"result": {"55555555": {"title": "Clinical Study on Skin Disease"}}}

    with patch("requests.get") as mock_get:
        r1 = MagicMock(status_code=200)
        r1.json.return_value = mock_esearch
        r2 = MagicMock(status_code=200)
        r2.json.return_value = mock_esummary
        mock_get.side_effect = [r1, r2]

        payload = {
            "text": "I am 34 years old and I have an itchy skin rash for 4 days."
        }
        resp = client.post('/api/cases', json=payload)
        assert resp.status_code == 201
        data = resp.json
        assert "id" in data
        assert data["specialist"] == "Dermatology"
        assert data["trace_count"] >= 5

        case_id = data["id"]

        # GET /api/cases/<id>
        detail_resp = client.get(f'/api/cases/{case_id}')
        assert detail_resp.status_code == 200
        detail = detail_resp.json
        assert detail["id"] == case_id
        assert len(detail["traces"]) >= 5
        assert len(detail["citations"]) >= 1

        # GET /api/cases (list)
        list_resp = client.get('/api/cases')
        assert list_resp.status_code == 200
        list_data = list_resp.json
        assert list_data["total"] >= 1
        assert len(list_data["cases"]) >= 1

        # GET /api/cases/<id>/report.pdf
        pdf_resp = client.get(f'/api/cases/{case_id}/report.pdf')
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["Content-Type"] == "application/pdf"
        assert len(pdf_resp.data) > 1000  # Substantial PDF byte length


def test_cases_chest_pain_2_hours_age_60_emergency(client):
    payload = {
        "text": "I am 60 years old and have had chest pain for two hours."
    }
    resp = client.post('/api/cases', json=payload)
    assert resp.status_code == 201
    data = resp.json
    assert data["severity"] == "EMERGENCY"
    assert data["score"] == 100
    assert data["specialist"] == "Emergency Medicine"
    assert "chest_pain" in data["symptoms"]
    assert data["age"] == 60
    assert 0.08 <= data["duration_days"] <= 0.09


def test_cases_mild_headache_stays_low(client):
    payload = {
        "text": "I am 54 years old and have had mild headache for two days."
    }
    resp = client.post('/api/cases', json=payload)
    assert resp.status_code == 201
    data = resp.json
    assert data["severity"] == "LOW"
    assert data["score"] < 8
    assert data["specialist"] == "Neurology"
    assert "headache" in data["symptoms"]
    assert data["duration_days"] == 2.0


def test_cases_get_not_found(client):
    resp = client.get('/api/cases/999999')
    assert resp.status_code == 404
    assert "error" in resp.json


def test_cases_pdf_not_found(client):
    resp = client.get('/api/cases/999999/report.pdf')
    assert resp.status_code == 404


def test_stats_endpoint(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    data = resp.json
    assert "total_cases" in data
    assert "emergency_cases" in data
    assert "specialties" in data
    assert "total_patients" in data


def test_patients_endpoint(client):
    resp = client.get('/api/patients?limit=5')
    assert resp.status_code == 200
    data = resp.json
    assert "total" in data
    assert "patients" in data
    assert len(data["patients"]) <= 5


def test_cases_with_synthea_patient_id(client):
    # Fetch a real patient from /api/patients
    resp = client.get('/api/patients?limit=1')
    assert resp.status_code == 200
    patients = resp.json.get("patients", [])
    if patients:
        patient_id = patients[0]["id"]
    else:
        patient_id = "0149d553-f571-4e99-867e-fcb9625d07c2"

    payload = {
        "text": "I am having mild stomach cramps and bloating for 2 days.",
        "patient_id": patient_id
    }
    case_resp = client.post('/api/cases', json=payload)
    assert case_resp.status_code == 201
    data = case_resp.json
    assert data["patient_id"] == patient_id
    assert data["patient_context_loaded"] is True
    assert "PATIENT CONTEXT" in data["narrative_summary"]


def test_cases_with_invalid_patient_id(client):
    payload = {
        "text": "I am having mild headache for 1 day.",
        "patient_id": "invalid-demo-patient-999"
    }
    case_resp = client.post('/api/cases', json=payload)
    assert case_resp.status_code == 201
    data = case_resp.json
    assert data["patient_context_loaded"] is False
    assert "not provided or unavailable" in data["narrative_summary"]


def test_patient_detail_endpoint(client):
    resp = client.get('/api/patients?limit=1')
    patients = resp.json.get("patients", [])
    if patients:
        patient_id = patients[0]["id"]
        detail_resp = client.get(f'/api/patients/{patient_id}')
        assert detail_resp.status_code == 200
        data = detail_resp.json
        assert data["id"] == patient_id
        assert "conditions" in data
        assert "encounters" in data

    # Test not found
    nf_resp = client.get('/api/patients/nonexistent-id-12345')
    assert nf_resp.status_code == 404
