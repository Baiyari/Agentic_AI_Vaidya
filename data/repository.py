import json
from typing import Optional, List
from sqlalchemy.orm import Session
from data.models import TriageRecord
from core.models import TriageRequest, TriageResult

class TriageRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_record(self, request: TriageRequest, result: TriageResult) -> TriageRecord:
        """
        Persists a triage request and result to the database.
        """
        record = TriageRecord(
            symptoms=json.dumps(request.symptoms),
            age=request.age,
            duration_days=request.duration_days,
            severity=result.severity.value,
            reason=result.reason,
            score=result.score,
            specialist=result.specialist_suggestion.specialist if result.specialist_suggestion else None
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_record(self, record_id: int) -> Optional[TriageRecord]:
        """
        Retrieves a triage record by ID.
        """
        return self.session.query(TriageRecord).filter(TriageRecord.id == record_id).first()
