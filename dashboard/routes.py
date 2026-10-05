import json
import logging
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_

from config.settings import settings
from data.database import SessionLocal
from data.models import TriageRecord, AgentTrace, EvidenceCitation, Patient, User
from core.models import SeverityLevel
from agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)

bp = Blueprint(
    'dashboard',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@bp.before_request
def before_request():
    g.db = SessionLocal()


@bp.teardown_request
def teardown_request(exception=None):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


# -------------------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------------------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = g.db.query(User).filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f"Welcome back, {user.full_name or user.username}.", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.overview'))
        else:
            flash("Invalid clinician credentials. Please try again.", "danger")

    return render_template('login.html', admin_user=settings.DASHBOARD_ADMIN_USER)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('dashboard.login'))


# -------------------------------------------------------------------------
# Dashboard Views
# -------------------------------------------------------------------------

@bp.route('/')
@bp.route('/dashboard')
@login_required
def overview():
    # KPI metrics
    total_cases = g.db.query(TriageRecord).count()
    emergency_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.EMERGENCY.value).count()
    high_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.HIGH.value).count()
    moderate_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.MODERATE.value).count()
    low_cases = g.db.query(TriageRecord).filter(TriageRecord.severity == SeverityLevel.LOW.value).count()

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    cases_today = g.db.query(TriageRecord).filter(TriageRecord.created_at >= today_start).count()
    total_patients = g.db.query(Patient).count()

    # Specialty distribution
    spec_rows = g.db.query(
        TriageRecord.specialist, func.count(TriageRecord.id)
    ).group_by(TriageRecord.specialist).all()

    specialty_counts = {
        (r[0] or "General Medicine"): r[1]
        for r in spec_rows
    }

    # Recent cases
    recent_cases = g.db.query(TriageRecord).order_by(TriageRecord.id.desc()).limit(7).all()

    return render_template(
        'overview.html',
        total_cases=total_cases,
        emergency_cases=emergency_cases,
        high_cases=high_cases,
        moderate_cases=moderate_cases,
        low_cases=low_cases,
        cases_today=cases_today,
        total_patients=total_patients,
        emergency_pct=round((emergency_cases / total_cases * 100), 1) if total_cases > 0 else 0,
        specialty_counts=specialty_counts,
        recent_cases=recent_cases
    )


@bp.route('/cases')
@login_required
def case_list():
    severity = request.args.get('severity', '')
    specialist = request.args.get('specialist', '')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 15

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

    total = query.count()
    records = query.order_by(TriageRecord.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'cases.html',
        cases=records,
        total=total,
        page=page,
        total_pages=total_pages,
        severity=severity,
        specialist=specialist,
        search=search
    )


@bp.route('/cases/<int:case_id>')
@login_required
def case_detail(case_id: int):
    record = g.db.query(TriageRecord).filter(TriageRecord.id == case_id).first()
    if not record:
        flash(f"Case #{case_id} not found.", "warning")
        return redirect(url_for('dashboard.case_list'))

    symptoms_list = []
    try:
        symptoms_list = json.loads(record.symptoms)
    except Exception:
        symptoms_list = [record.symptoms]

    return render_template(
        'case_detail.html',
        case=record,
        symptoms=symptoms_list,
        traces=record.traces,
        citations=record.citations
    )


@bp.route('/intake', methods=['GET', 'POST'])
@login_required
def intake():
    patient_id = request.args.get('patient_id')
    selected_patient = None
    if patient_id:
        selected_patient = g.db.query(Patient).filter(Patient.id == patient_id).first()

    if request.method == 'POST':
        narrative_text = request.form.get('narrative_text', '').strip()
        patient_id_form = request.form.get('patient_id', '').strip() or None

        if not narrative_text:
            flash("Please enter clinical notes or patient narrative.", "warning")
            return redirect(url_for('dashboard.intake', patient_id=patient_id_form))

        record, ctx = orchestrator.process_case(
            raw_text=narrative_text,
            session=g.db,
            patient_id=patient_id_form
        )

        flash(f"Case #{record.id} successfully analyzed by Vaidya Multi-Agent Pipeline.", "success")
        return redirect(url_for('dashboard.case_detail', case_id=record.id))

    return render_template('intake.html', selected_patient=selected_patient)


@bp.route('/patients')
@login_required
def patient_list():
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20

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
    patients = query.order_by(Patient.last_name.asc()).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'patients.html',
        patients=patients,
        total=total,
        page=page,
        total_pages=total_pages,
        search=search
    )
