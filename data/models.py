import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from data.database import Base


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class TriageRecord(Base):
    """
    Persisted clinical record for an incoming patient triage/case.
    """
    __tablename__ = "triage_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    chief_complaint = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=False)  # Stored as JSON string list of symptoms
    age = Column(Integer, nullable=False)
    duration_days = Column(Float, nullable=False, default=1.0)
    duration_hours = Column(Float, nullable=True)
    severity = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)
    specialist = Column(String(100), nullable=True, index=True)
    narrative_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    patient = relationship("Patient", back_populates="triage_records")
    traces = relationship("AgentTrace", back_populates="case", cascade="all, delete-orphan", order_by="AgentTrace.id")
    citations = relationship("EvidenceCitation", back_populates="case", cascade="all, delete-orphan", order_by="EvidenceCitation.id")


class AgentTrace(Base):
    """
    Audit log / trace entry for every agent decision step in a case pipeline.
    """
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("triage_records.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    case = relationship("TriageRecord", back_populates="traces")


class EvidenceCitation(Base):
    """
    PubMed / medical literature citation associated with a clinical recommendation.
    """
    __tablename__ = "evidence_citations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("triage_records.id", ondelete="CASCADE"), nullable=False, index=True)
    pmid = Column(String(32), nullable=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    relevance_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    case = relationship("TriageRecord", back_populates="citations")


class Patient(Base):
    """
    Synthetic patient demographic record imported from Synthea EHR data.
    """
    __tablename__ = "patients"

    id = Column(String(64), primary_key=True, index=True)
    birthdate = Column(String(32), nullable=True)
    deathdate = Column(String(32), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    gender = Column(String(10), nullable=True)
    race = Column(String(50), nullable=True)
    ethnicity = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip = Column(String(20), nullable=True)

    # Relationships
    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    triage_records = relationship("TriageRecord", back_populates="patient")

    @property
    def full_name(self) -> str:
        first = self.first_name or ""
        last = self.last_name or ""
        return f"{first} {last}".strip() or "Unknown Patient"


class Condition(Base):
    """
    Synthea condition / diagnosed problem record.
    """
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), nullable=True)
    code = Column(String(64), nullable=True, index=True)
    description = Column(Text, nullable=False)
    start_date = Column(String(32), nullable=True)
    stop_date = Column(String(32), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="conditions")


class Encounter(Base):
    """
    Synthea encounter / clinical visit record.
    """
    __tablename__ = "encounters"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(String(32), nullable=True)
    stop_date = Column(String(32), nullable=True)
    encounter_class = Column(String(50), nullable=True)
    code = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="encounters")


class User(Base, UserMixin):
    """
    Clinician / administrative user for the Vaidya clinical dashboard.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(120), nullable=True)
    role = Column(String(32), default="clinician")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
