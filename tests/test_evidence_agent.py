from unittest.mock import patch, MagicMock
from agents.evidence_agent import EvidenceRetrievalAgent
from data.models import EvidenceCitation, TriageRecord


def test_evidence_agent_success(db_session):
    agent = EvidenceRetrievalAgent(request_delay_seconds=0.0)

    # Create dummy triage record
    record = TriageRecord(
        symptoms='["chest_pain"]',
        age=50,
        duration_days=1,
        severity="HIGH",
        reason="High risk",
        score=15
    )
    db_session.add(record)
    db_session.commit()

    mock_esearch = {
        "esearchresult": {
            "idlist": ["12345678", "87654321"]
        }
    }
    mock_esummary = {
        "result": {
            "12345678": {"title": "Clinical Guidelines for Acute Coronary Syndrome"},
            "87654321": {"title": "High-sensitivity Cardiac Troponin in Emergency Care"}
        }
    }

    with patch("requests.get") as mock_get:
        # First call is esearch, second is esummary
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = mock_esearch

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = mock_esummary

        mock_get.side_effect = [resp1, resp2]

        citations = agent.retrieve(
            evidence_terms=["acute coronary syndrome"],
            session=db_session,
            case_id=record.id
        )

        assert len(citations) == 2
        assert citations[0]["pmid"] == "12345678"
        assert "Acute Coronary Syndrome" in citations[0]["title"]
        assert "https://pubmed.ncbi.nlm.nih.gov/12345678/" in citations[0]["url"]

        # Check that citations were persisted in DB
        db_citations = db_session.query(EvidenceCitation).filter(EvidenceCitation.case_id == record.id).all()
        assert len(db_citations) == 2

        # Verify caching: second call with same case_id should hit DB cache without calling requests.get
        mock_get.reset_mock()
        cached_citations = agent.retrieve(
            evidence_terms=["acute coronary syndrome"],
            session=db_session,
            case_id=record.id
        )
        assert len(cached_citations) == 2
        mock_get.assert_not_called()


def test_evidence_agent_offline_resilience(db_session):
    agent = EvidenceRetrievalAgent(request_delay_seconds=0.0)

    with patch("requests.get", side_effect=Exception("Network unreachable")):
        citations = agent.retrieve(
            evidence_terms=["asthma exacerbation"],
            session=db_session,
            case_id=None
        )
        assert len(citations) == 1
        assert "asthma exacerbation" in citations[0]["title"]
        assert "https://pubmed.ncbi.nlm.nih.gov/?term=" in citations[0]["url"]
