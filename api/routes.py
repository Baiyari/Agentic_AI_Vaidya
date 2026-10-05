import json
import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, g, send_file
from pydantic import ValidationError
from sqlalchemy import func, or_

from api.schemas import TriageRequestPayload, CaseCreatePayload
from api.pdf_generator import generate_case_pdf
from core.models import TriageRequest, SeverityLevel
from core.triage import assess_severity
from core.exceptions import VaidyaError, TriageValidationError
from data.database import SessionLocal
from data.models import TriageRecord, AgentTrace, EvidenceCitation, Patient
from data.repository import TriageRepository
from agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)
bp = Blueprint('api', __name__, url_prefix='/api')


@bp.before_request
def before_request():
    """Setup DB session for the request (excluding healthcheck)."""
    if request.path == '/api/health':
        g.db = None
        return
    g.db = SessionLocal()


@bp.teardown_request
def teardown_request(exception=None):
    """Close DB session if opened."""
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@bp.route('/health', methods=['GET'])
def health_check():
    """Liveness check endpoint."""
    return jsonify({"status": "ok", "app": "Vaidya Health-Triage Advisor"}), 200


# -------------------------------------------------------------------------
# Multi-Agent Case Endpoints
# -------------------------------------------------------------------------

@bp.route('/cases', methods=['POST'])
def create_case():
    """
    Accepts natural language patient intake, runs the full multi-agent
    decision support pipeline, and returns the case summary.
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Missing or invalid JSON body"}), 400

        case_in = CaseCreatePayload(**payload)
        record, ctx = orchestrator.process_case(
            raw_text=case_in.text,
            session=g.db,
            patient_id=case_in.patient_id
        )

        return jsonify({
            "id": record.id,
            "patient_id": record.patient_id,
            "patient_context_loaded": ctx.patient_context_loaded,
            "severity": record.severity,
            "score": record.score,
            "specialist": record.specialist,
            "reason": record.reason,
            "symptoms": json.loads(record.symptoms),
            "age": record.age,
            "duration_days": record.duration_days,
            "narrative_summary": record.narrative_summary,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "trace_count": len(record.traces),
            "citation_count": len(record.citations)
        }), 201

    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except Exception as e:
        logger.exception("Error processing multi-agent case intake.")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@bp.route('/cases', methods=['GET'])
def list_cases():
    """
    Returns a paginated, filterable list of clinical cases.
    Query parameters: severity, specialist, search, limit, offset.
    """
    try:
        severity = request.args.get('severity')
        specialist = request.args.get('specialist')
        search = request.args.get('search')
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))

        query = g.db.query(TriageRecord)

        if severity:
            query = query.filter(TriageRecord.severity == severity.upper())
        if specialist:
            query = query.filter(TriageRecord.specialist.ilike(f"%{specialist}%"))
        if search:
            query = query.filter(
                or_(
                    TriageRecord.chief_complaint.ilike(f"%{search}%"),
                    TriageRecord.symptoms.ilike(f"%{search}%"),
                    TriageRecord.patient_id.ilike(f"%{search}%")
                )
            )

        total_count = query.count()
        records = query.order_by(TriageRecord.id.desc()).offset(offset).limit(limit).all()

        cases_data = []
        for r in records:
            cases_data.append({
                "id": r.id,
                "patient_id": r.patient_id,
                "chief_complaint": r.chief_complaint,
                "symptoms": json.loads(r.symptoms) if r.symptoms else [],
                "age": r.age,
                "duration_days": r.duration_days,
                "severity": r.severity,
                "score": r.score,
                "specialist": r.specialist,
                "reason": r.reason,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })

        return jsonify({
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "cases": cases_data
        }), 200

    except Exception as e:
        logger.exception("Error listing cases.")
        return jsonify({"error": "Internal server error"}), 500


@bp.route('/cases/<int:case_id>', methods=['GET'])
def get_case_detail(case_id: int):
    """
    Retrieves complete case details including the full AgentTrace timeline and citations.
    """
    record = g.db.query(TriageRecord).filter(TriageRecord.id == case_id).first()
    if not record:
        return jsonify({"error": "Case record not found"}), 404

    traces = [
        {
            "id": t.id,
            "agent_name": t.agent_name,
            "input_summary": t.input_summary,
            "output_summary": t.output_summary,
            "reasoning": t.reasoning,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in record.traces
    ]

    citations = [
        {
            "id": c.id,
            "pmid": c.pmid,
            "title": c.title,
            "url": c.url,
            "relevance_note": c.relevance_note
        }
        for c in record.citations
    ]

    return jsonify({
        "id": record.id,
        "patient_id": record.patient_id,
        "chief_complaint": record.chief_complaint,
        "symptoms": json.loads(record.symptoms) if record.symptoms else [],
        "age": record.age,
        "duration_days": record.duration_days,
        "severity": record.severity,
        "score": record.score,
        "specialist": record.specialist,
        "reason": record.reason,
        "narrative_summary": record.narrative_summary,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "traces": traces,
        "citations": citations
    }), 200


@bp.route('/cases/<int:case_id>/report.pdf', methods=['GET'])
def download_case_pdf(case_id: int):
    """
    Generates and streams a professional referral and escalation PDF report.
    """
    record = g.db.query(TriageRecord).filter(TriageRecord.id == case_id).first()
    if not record:
        return jsonify({"error": "Case record not found"}), 404

    pdf_buffer = generate_case_pdf(record)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"vaidya_referral_case_{case_id}.pdf"
    )


# -------------------------------------------------------------------------
# Clinical Analytics & Patient Endpoints
# -------------------------------------------------------------------------

@bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Returns clinical KPIs and distribution metrics for Chart.js dashboard.
    """
    try:
        total_cases = g.db.query(TriageRecord).count()
        emergency_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.EMERGENCY.value).count()
        high_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.HIGH.value).count()
        moderate_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.MODERATE.value).count()
        low_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.LOW.value).count()

        # Cases today
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        cases_today = g.db.query(TriageRecord).filter(TriageRecord.created_at >= today_start).count()

        # Specialty breakdown
        specialty_rows = g.db.query(
            TriageRecord.specialist, func.count(TriageRecord.id)
        ).group_by(TriageRecord.specialist).all()

        specialties_distribution = {
            (row[0] or "General Medicine"): row[1]
            for row in specialty_rows
        }

        total_patients = g.db.query(Patient).count()

        return jsonify({
            "total_cases": total_cases,
            "emergency_cases": emergency_cases,
            "high_cases": high_cases,
            "moderate_cases": moderate_cases,
            "low_cases": low_cases,
            "cases_today": cases_today,
            "emergency_percentage": round((emergency_cases / total_cases * 100), 1) if total_cases > 0 else 0.0,
            "specialties": specialties_distribution,
            "total_patients": total_patients
        }), 200

    except Exception as e:
        logger.exception("Error computing statistics.")
        return jsonify({"error": "Internal server error"}), 500


@bp.route('/patients', methods=['GET'])
def list_patients():
    """
    Returns a browsable, searchable list of Synthea EHR synthetic patients.
    """
    try:
        search = request.args.get('search')
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))

        query = g.db.query(Patient)
        if search:
            query = query.filter(
                or_(
                    Patient.first_name.ilike(f"%{search}%"),
                    Patient.last_name.ilike(f"%{search}%"),
                    Patient.id.ilike(f"%{search}%"),
                    Patient.city.ilike(f"%{search}%")
                )
            )

        total = query.count()
        patients = query.order_by(Patient.last_name.asc()).offset(offset).limit(limit).all()

        patient_list = [
            {
                "id": p.id,
                "name": p.full_name,
                "gender": p.gender,
                "birthdate": p.birthdate,
                "city": p.city,
                "state": p.state,
                "condition_count": len(p.conditions)
            }
            for p in patients
        ]

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "patients": patient_list
        }), 200

    except Exception as e:
        logger.exception("Error listing patients.")
        return jsonify({"error": "Internal server error"}), 500


@bp.route('/patients/<string:patient_id>', methods=['GET'])
def get_patient_detail(patient_id: str):
    """
    Retrieves a single Synthea patient by ID with their condition history and encounters.
    """
    try:
        patient = g.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        conditions = [
            {
                "code": c.code,
                "description": c.description,
                "start_date": c.start_date,
                "stop_date": c.stop_date
            }
            for c in patient.conditions
        ]

        encounters = [
            {
                "id": e.id,
                "start_date": e.start_date,
                "stop_date": e.stop_date,
                "code": e.code,
                "description": e.description,
                "encounter_class": e.encounter_class
            }
            for e in patient.encounters
        ]

        return jsonify({
            "id": patient.id,
            "name": patient.full_name,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "gender": patient.gender,
            "birthdate": patient.birthdate,
            "city": patient.city,
            "state": patient.state,
            "conditions": conditions,
            "encounters": encounters
        }), 200

    except Exception as e:
        logger.exception(f"Error fetching patient {patient_id}.")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------------------------------------------------------
# Legacy Triage Endpoints (Backward Compatible with existing tests & MCP)
# -------------------------------------------------------------------------

@bp.route('/triage', methods=['POST'])
def run_triage():
    """
    Legacy deterministic triage endpoint maintained for backwards compatibility.
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid or missing JSON body."}), 400

        validated_data = TriageRequestPayload(**payload)
        triage_request = TriageRequest(
            symptoms=validated_data.symptoms,
            age=validated_data.age,
            duration_days=validated_data.duration_days,
            duration_hours=validated_data.duration_hours
        )

        result = assess_severity(triage_request)
        repo = TriageRepository(g.db)
        record = repo.create_record(triage_request, result)

        response_data = {
            "id": record.id,
            "severity": result.severity.value,
            "reason": result.reason,
            "matched_symptoms": result.matched_symptoms,
            "score": result.score,
            "specialist_suggestion": result.specialist_suggestion.model_dump() if result.specialist_suggestion else None
        }
        return jsonify(response_data), 200

    except ValidationError as e:
        return jsonify({"error": "Invalid input data", "details": e.errors()}), 400
    except TriageValidationError as e:
        return jsonify({"error": str(e)}), 400
    except VaidyaError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error during triage.")
        return jsonify({"error": "Internal server error"}), 500


@bp.route('/triage/<int:record_id>', methods=['GET'])
def get_triage(record_id: int):
    """Legacy triage record retrieval endpoint."""
    repo = TriageRepository(g.db)
    record = repo.get_record(record_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    return jsonify({
        "id": record.id,
        "symptoms": json.loads(record.symptoms),
        "age": record.age,
        "duration_days": record.duration_days,
        "severity": record.severity,
        "reason": record.reason,
        "score": record.score,
        "specialist": record.specialist,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }), 200
