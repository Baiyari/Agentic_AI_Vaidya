import pytest
from unittest.mock import patch, MagicMock
from config.settings import settings
from data.models import User, TriageRecord


def test_dashboard_login_flow(client, db_session):
    # Ensure admin user exists in test DB
    admin = db_session.query(User).filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", full_name="Dr. Vaidya", role="clinician")
        admin.set_password("vaidya123")
        db_session.add(admin)
        db_session.commit()

    # 1. Unauthenticated request to / should redirect to /login
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # 2. GET /login should display login form
    login_page = client.get('/login')
    assert login_page.status_code == 200
    assert b"Vaidya Portal" in login_page.data

    # 3. POST /login with invalid credentials should fail
    bad_login = client.post('/login', data={"username": "admin", "password": "wrongpassword"}, follow_redirects=True)
    assert b"Invalid clinician credentials" in bad_login.data

    # 4. POST /login with correct credentials should succeed
    good_login = client.post('/login', data={"username": "admin", "password": "vaidya123"}, follow_redirects=True)
    assert good_login.status_code == 200
    assert b"Clinical Overview" in good_login.data

    # 5. GET /cases should display case directory
    cases_resp = client.get('/cases')
    assert cases_resp.status_code == 200
    assert b"Clinical Cases Directory" in cases_resp.data

    # 6. GET /intake should display intake form
    intake_resp = client.get('/intake')
    assert intake_resp.status_code == 200
    assert b"Conversational Case Intake" in intake_resp.data

    # 7. POST /intake should analyze case and redirect to case detail
    mock_esearch = {"esearchresult": {"idlist": ["11112222"]}}
    mock_esummary = {"result": {"11112222": {"title": "Clinical Assessment of Acute Headache"}}}

    with patch("requests.get") as mock_get:
        r1 = MagicMock(status_code=200)
        r1.json.return_value = mock_esearch
        r2 = MagicMock(status_code=200)
        r2.json.return_value = mock_esummary
        mock_get.side_effect = [r1, r2]

        post_intake = client.post('/intake', data={
            "narrative_text": "I am a 35 year old female with a severe headache and dizziness for 2 days."
        }, follow_redirects=True)

        assert post_intake.status_code == 200
        assert b"Multi-Agent Execution Timeline" in post_intake.data
        assert b"Intake Agent" in post_intake.data
        assert b"Safety Triage Agent" in post_intake.data

    # 8. GET /patients should display Synthea cohort
    patients_resp = client.get('/patients')
    assert patients_resp.status_code == 200
    assert b"Synthea EHR Synthetic Cohort" in patients_resp.data

    # 9. GET /logout should sign out
    logout_resp = client.get('/logout', follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"signed out safely" in logout_resp.data
