# Vaidya: Autonomous Multi-Agent Health-Advisory System

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16--alpine-blue.svg)](https://www.postgresql.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-black.svg)](https://flask.palletsprojects.com/)
[![Alembic](https://img.shields.io/badge/Alembic-1.20-red.svg)](https://alembic.sqlalchemy.org/)
[![FastMCP](https://img.shields.io/badge/FastMCP-4.0.2-purple.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Vaidya** is an explainable, auditable, evidence-backed clinical multi-agent decision support system designed for graded academic Agentic AI assessment (60 marks). It integrates a **100% deterministic safety rule engine**, specialized clinical agents (Cardiology, Pulmonology, Neurology, Gastroenterology, Dermatology, General Medicine), real-time **PubMed E-utilities RAG** literature grounding, **Synthea EHR** synthetic patient ingestion, and a modern **Flask clinical dashboard** styled with Tailwind CSS and Chart.js.

---

## 1. System Architecture

```mermaid
flowchart TD
    U["Patient Conversational Input<br/>(Natural Language Narrative)"] --> IA["Intake Agent<br/>(Regex / Keyword Taxonomy Fallback + Optional Gemini)"]
    IA --> TA["Deterministic Safety Triage Agent<br/>(core/triage.py — 100% Rule-Based, ZERO LLM)"]
    TA -->|"EMERGENCY (Short-circuit)"| ESC["Immediate Escalation Path"]
    TA -->|"Non-Emergency"| SR["Specialty Router Agent<br/>(100+ Entry Clinical Taxonomy)"]
    SR --> SPEC{"Specialist Agent Pool<br/>(BaseSpecialistAgent)"}
    SPEC --> CARD["Cardiology Agent"]
    SPEC --> PULM["Pulmonology Agent"]
    SPEC --> NEURO["Neurology Agent"]
    SPEC --> GI["Gastroenterology Agent"]
    SPEC --> DERM["Dermatology Agent"]
    SPEC --> GEN["General Medicine Agent"]
    CARD & PULM & NEURO & GI & DERM & GEN --> EV["Evidence Retrieval Agent<br/>(NCBI PubMed E-Utilities RAG)"]
    EV --> EXP["Explainability / Summary Agent<br/>(Clinical Synthesis & Citations)"]
    ESC --> EXP
    EXP --> DB[("PostgreSQL 16 Database<br/>(TriageRecord, AgentTrace, EvidenceCitation)")]
    EXP --> PDF["Referral & Escalation Report<br/>(PDF Generation via ReportLab)"]
    DB --> DASH["Flask Clinical Dashboard<br/>(KPI Cards, Chart.js Analytics, Trace Timeline)"]
```

### Agent Roster & Operating Constraints

| Agent | Input | Output | LLM Usage | Deterministic Fallback |
|---|---|---|---|---|
| **Intake Agent** | Unstructured patient narrative | Structured `TriageRequest` (symptoms, age, duration) | Optional (Gemini free tier) | Regex + 103-entry medical taxonomy matching |
| **Safety Triage Agent** | `TriageRequest` | `SeverityLevel` (EMERGENCY / HIGH / MODERATE / LOW), score, reason | **NEVER (Zero LLM)** | 100% deterministic rule-based evaluation |
| **Specialty Router** | Extracted symptoms | Ranked candidate specialties | None | Table-driven taxonomy frequency weighting |
| **Specialist Agents** (Pool of 6) | Case context + triage score | Differential diagnoses, reasoning, diagnostic actions, PubMed terms | Optional (Gemini) | Template-based pathophysiological reasoning |
| **Evidence Agent** | Specialist key search terms | 2–3 peer-reviewed PubMed citations (Title, PMID, URL, relevance) | None | NCBI E-utilities (`esearch` + `esummary`) + DB cache |
| **Explainability Agent** | Complete multi-agent trace | Clinical referral report & patient discharge recommendations | Optional (Gemini) | Clinician referral template with citations |

---

## 2. Key Design Rationales (Viva & Defense Ready)

### A. Why Safety Triage Remains 100% Deterministic (Zero LLM)
In healthcare AI, **hallucination, stochastic non-determinism, and prompt injection pose unacceptable patient safety risks**. Medical emergency categorization must be auditable, reproducible, and verifiable under law and clinical governance. In Vaidya:
1. Red-flag combinations (e.g. `chest_pain` + `shortness_of_breath`, `slurred_speech` + `facial_drooping`, `fever` + `stiff_neck` + `confusion`) execute deterministic lookups with mathematical certainty.
2. An identical case presented 10,000 times will produce the exact same severity score and clinical categorization.
3. Unit tests verify 100% of red-flag paths without needing mocked model responses or internet connectivity.
4. When an emergency is detected, the system **short-circuits immediately**, bypassing non-urgent routing and notifying emergency care without latency.

### B. Why NCBI PubMed E-Utilities for Evidence Retrieval ($0 RAG)
1. **Authoritative & Peer-Reviewed:** Direct integration with the US National Library of Medicine (NLM) provides indexed biomedical literature.
2. **Zero API Cost ($0):** NCBI E-utilities (`esearch.fcgi`, `esummary.fcgi`) require no subscription or paid API keys.
3. **Targeted Grounding:** Rather than querying PubMed with noisy raw patient prose, queries are formulated directly from the **Specialist Agent's differential diagnosis and evidence terms**, yielding high-precision results.
4. **Persistent Caching:** Citations are cached per case in the PostgreSQL `evidence_citations` table, eliminating redundant network calls.

### C. Full Auditability via `AgentTrace`
Every agent in the pipeline writes an immutable record to the `agent_traces` table:
- Agent Name
- Input summary digest
- Decision output
- Step reasoning
- Precise UTC timestamp

This forms the "explainable" backbone of the platform, visually displayed as an interactive audit timeline in the clinician dashboard.

---

## 3. Technology Stack & Prerequisites

- **Python:** 3.11 / 3.13
- **Database:** PostgreSQL 16 (via official `postgres:16-alpine` Docker container)
- **Database Migrations:** Alembic
- **Web Framework:** Flask 3.0 + Flask-Login
- **Tool Protocol:** FastMCP (streamable-http on port 8000)
- **PDF Generation:** ReportLab
- **Frontend:** Jinja2, Tailwind CSS (CDN), FontAwesome 6, Chart.js
- **Synthetic EHR:** Synthea (500 patients, ~20k encounters, ~3.3k conditions seeded)

---

## 4. Setup & Quickstart

### Step 1: Clone and Create Virtual Environment
```bash
git clone <repo-url>
cd Vaidya
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration values:
```ini
APP_NAME="Vaidya Health-Triage Advisor"
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
DATABASE_URL=postgresql+psycopg2://vaidya:vaidya@localhost:5433/vaidya
LOG_LEVEL=INFO
GEMINI_API_KEY=
SECRET_KEY=vaidya-secret-clinical-key-2026
DASHBOARD_ADMIN_USER=admin
DASHBOARD_ADMIN_PASSWORD=vaidya123
MCP_HOST=127.0.0.1
MCP_PORT=8000
```

### Step 3: Start PostgreSQL Container
```bash
docker compose up -d postgres
```
*(Runs PostgreSQL 16 on host port 5433 mapped to container 5432, preventing collisions with existing host database services).*

### Step 4: Run Migrations and Seed Synthea Data
```bash
# Apply database schema migrations
alembic upgrade head

# Ingest Synthea EHR dataset (patients, encounters, conditions, demo user)
python scripts/seed_synthea.py
```

### Step 5: Launch Vaidya Services
```bash
python run.py
```
This launches:
- **Flask Clinical Dashboard & API:** `http://127.0.0.1:5000`
- **FastMCP Tool Server:** `http://127.0.0.1:8000`

---

## 5. Clinical Dashboard Walkthrough

Navigate to `http://localhost:5000` in your browser:
- **Clinician Login:** Username `admin` | Password `vaidya123`
- **Pages Available:**
  1. **Overview (`/`):** Real-time KPI cards, Chart.js severity doughnut chart, specialty distribution bar chart, recent cases list.
  2. **Cases Directory (`/cases`):** Filter cases by severity acuity, specialty, or search terms.
  3. **Case Detail (`/cases/<id>`):** Deterministic triage status, clinical assessment, PubMed citations, and the interactive **AgentTrace** timeline.
  4. **Conversational Intake (`/intake`):** Natural language intake with preset buttons for immediate testing (Emergency, Dermatology, Neurology, Pulmonology, etc.).
  5. **Synthea EHR Cohort (`/patients`):** Browsable demographic records of seeded patients with one-click triage initiation.
  6. **Referral PDF Export (`/api/cases/<id>/report.pdf`):** One-click download of a formalized medical referral report.

---

## 6. REST API Reference

### 1. Multi-Agent Conversational Intake
`POST /api/cases`
```json
{
  "text": "I am 54 years old and experiencing severe chest pain and breathlessness for 1 day.",
  "patient_id": "optional-synthea-uuid"
}
```
**Response (201 Created):**
```json
{
  "id": 1,
  "severity": "EMERGENCY",
  "score": 100,
  "specialist": "Emergency Medicine",
  "reason": "Critical red-flag combination detected: chest_pain, shortness_of_breath",
  "symptoms": ["chest_pain", "shortness_of_breath"],
  "age": 54,
  "duration_days": 1,
  "trace_count": 4,
  "citation_count": 0
}
```

### 2. Case Detail with Full Trace
`GET /api/cases/<id>`
Returns full case object including `traces` list and `citations` list.

### 3. Generate Referral PDF
`GET /api/cases/<id>/report.pdf`
Streams an application/pdf document generated on-the-fly using ReportLab.

### 4. Clinical KPIs & Distribution Statistics
`GET /api/stats`
Returns total case volume, emergency counts, and specialty distributions for Chart.js.

### 5. Synthea EHR Directory
`GET /api/patients?limit=20&search=Smith`

### 6. Deterministic Triage (Legacy / Backward-Compatible)
`POST /api/triage`
```json
{
  "symptoms": ["chest_pain", "shortness_of_breath"],
  "age": 45,
  "duration_days": 1
}
```

---

## 7. Automated Test Suite

Run the full pytest suite against PostgreSQL:
```bash
pytest tests/ -v
```
**Coverage Summary (68 passing tests):**
- `tests/test_triage.py`: 100% of red-flag combinations and scoring boundary paths.
- `tests/test_icd_lookup.py`: Validation of the 100+ entry medical taxonomy across 8 clinical specialties.
- `tests/test_specialists.py`: All 6 specialist agents verified in zero-LLM template mode.
- `tests/test_evidence_agent.py`: PubMed E-utilities search and PostgreSQL citation caching (mocked HTTP).
- `tests/test_orchestrator.py`: E2E emergency short-circuit test and full multi-agent pipeline trace test.
- `tests/test_api.py`: Comprehensive coverage of all REST routes, error handling, and PDF generation.
- `tests/test_dashboard.py`: Session authentication, login/logout, and all dashboard views.

---

## 8. Definition of Done Checklist

- [x] Deterministic triage logic is 100% rule-based (zero LLM calls) with 100% red-flag test coverage.
- [x] System runs entirely against PostgreSQL 16 (SQLite retained only as optional fallback).
- [x] Synthea EHR dataset seeded into PostgreSQL and used by the dashboard's Patients page and analytics.
- [x] Conversational intake flows through Intake → Safety Triage → Specialty Router → Specialist Agent → Evidence Agent → Explainability Agent → stored `AgentTrace`.
- [x] Emergency cases short-circuit immediately with audit trace.
- [x] PubMed literature citations retrieved and cached in PostgreSQL without paid API keys.
- [x] Professional Flask dashboard with Jinja2, Tailwind CSS, and Chart.js.
- [x] Referral PDF report generated and downloadable.
- [x] Operates seamlessly without `GEMINI_API_KEY` using deterministic fallbacks.
- [x] Full test suite (68 tests) passing against PostgreSQL.
- [x] FastMCP tool server preserved for generic LLM client interoperability.
- [x] Clean architecture, type hints, Pydantic schemas, and repository pattern maintained throughout.
