"""
Smoke test for Vaidya evaluation harness.
Runs 3 representative cases through the offline evaluation pipeline.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Isolate environment for test
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["USE_SQLITE"] = "1"

from data.database import Base
from evaluation.run_eval import evaluate_single_case, get_mock_pubmed
from evaluation.metrics import calculate_safety_metrics, calculate_routing_metrics, calculate_intake_metrics


@pytest.fixture
def eval_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_eval_harness_smoke(eval_db):
    test_cases = [
        {
            "id": "smoke_001",
            "text": "I am 60 years old and have had chest pain for two hours.",
            "expected_symptoms": ["chest_pain"],
            "expected_age": 60,
            "expected_duration_days": 0.083,
            "expected_severity": "EMERGENCY",
            "expected_specialty": "Emergency Medicine",
            "category": "red_flag"
        },
        {
            "id": "smoke_002",
            "text": "I am 26 years old and have had an itchy red skin rash for 5 days.",
            "expected_symptoms": ["skin_rash"],
            "expected_age": 26,
            "expected_duration_days": 5.0,
            "expected_severity": "LOW",
            "expected_specialty": "Dermatology",
            "category": "routine"
        },
        {
            "id": "smoke_003",
            "text": "I am 54 years old and have had mild headache for two days.",
            "expected_symptoms": ["headache"],
            "expected_age": 54,
            "expected_duration_days": 2.0,
            "expected_severity": "LOW",
            "expected_specialty": "Neurology",
            "category": "routine"
        }
    ]

    with patch("requests.get", get_mock_pubmed()):
        results = []
        for case in test_cases:
            res = evaluate_single_case(case, eval_db)
            results.append(res)

        assert len(results) == 3
        safety = calculate_safety_metrics(results)
        routing = calculate_routing_metrics(results)
        intake = calculate_intake_metrics(results)

        assert safety["emergency_recall"] == 1.0
        assert len(safety["missed_emergencies"]) == 0
        assert routing["specialty_top1_accuracy"] >= 0.66
        assert intake["age_exact_match_rate"] == 1.0
